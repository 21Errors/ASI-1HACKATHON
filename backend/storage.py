"""
LeadStorage - Simple JSON file storage for lead pipeline tracking
No database needed, uses JSON file at data/leads.json with file locking
"""
import json
import os
import uuid
from threading import Lock
from typing import Dict, List, Optional
from datetime import datetime


class LeadStorage:
    """Store and retrieve leads from JSON file"""
    
    def __init__(self, data_dir: str = "data", filename: str = "leads.json"):
        """
        Initialize storage with data directory and file
        
        Args:
            data_dir: Directory for data files (default: "data")
            filename: Filename for leads (default: "leads.json")
        """
        self.data_dir = data_dir
        self.filepath = os.path.join(data_dir, filename)
        self._lock = Lock()
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        
        # Create empty leads file if it doesn't exist
        if not os.path.exists(self.filepath):
            self._write_leads([])
    
    def _read_leads(self) -> List[Dict]:
        """Read all leads from JSON file (thread-safe)"""
        with self._lock:
            try:
                if not os.path.exists(self.filepath):
                    return []
                
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return []
                    return json.loads(content)
            
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading leads: {e}")
                return []
    
    def _write_leads(self, leads: List[Dict]) -> None:
        """Write all leads to JSON file (thread-safe)"""
        with self._lock:
            try:
                # Ensure directory exists
                os.makedirs(self.data_dir, exist_ok=True)
                
                # Write with proper formatting
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump(leads, f, indent=2, ensure_ascii=False)
            
            except IOError as e:
                print(f"Error writing leads: {e}")
    
    def save_lead(self, lead_dict: Dict) -> Dict:
        """
        Save a new lead with auto-generated UUID
        
        Args:
            lead_dict: Lead data (without id and timestamps)
        
        Returns:
            Lead dict with id, created_at, and all fields
        """
        lead = {
            "id": str(uuid.uuid4()),
            "business_name": lead_dict.get("business_name", ""),
            "city": lead_dict.get("city", ""),
            "country": lead_dict.get("country", ""),
            "industry": lead_dict.get("industry", ""),
            "website": lead_dict.get("website", None),
            "phone": lead_dict.get("phone", None),
            "has_website": lead_dict.get("has_website", False),
            "service": lead_dict.get("service", ""),
            "fit_score": lead_dict.get("fit_score", None),
            "pain_points": lead_dict.get("pain_points", []),
            "best_angle": lead_dict.get("best_angle", ""),
            "email_subject": lead_dict.get("email_subject", ""),
            "email_body": lead_dict.get("email_body", ""),
            "to_email": lead_dict.get("to_email", None),
            "contact_email": lead_dict.get("contact_email", None),
            "email_source": lead_dict.get("email_source", "not_found"),
            "status": lead_dict.get("status", "researched"),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "sent_at": None,
            "opened_at": None,
            "replied_at": None,
            "notes": lead_dict.get("notes", "")
        }
        
        # Read all leads, append new one, write back
        leads = self._read_leads()
        leads.append(lead)
        self._write_leads(leads)
        
        return lead
    
    def update_lead(self, lead_id: str, updates_dict: Dict) -> Optional[Dict]:
        """
        Update an existing lead with partial updates
        
        Args:
            lead_id: ID of lead to update
            updates_dict: Dictionary with fields to update
        
        Returns:
            Updated lead dict, or None if not found
        """
        leads = self._read_leads()
        
        for i, lead in enumerate(leads):
            if lead.get("id") == lead_id:
                # Update fields, but protect certain ones
                for key, value in updates_dict.items():
                    if key not in ["id", "created_at"]:
                        lead[key] = value
                
                # Update status-related timestamps
                if "status" in updates_dict:
                    status = updates_dict["status"]
                    if status == "sent" and not lead.get("sent_at"):
                        lead["sent_at"] = datetime.utcnow().isoformat() + "Z"
                    elif status == "opened" and not lead.get("opened_at"):
                        lead["opened_at"] = datetime.utcnow().isoformat() + "Z"
                    elif status == "replied" and not lead.get("replied_at"):
                        lead["replied_at"] = datetime.utcnow().isoformat() + "Z"
                
                leads[i] = lead
                self._write_leads(leads)
                return lead
        
        return None
    
    def get_lead(self, lead_id: str) -> Optional[Dict]:
        """
        Get a single lead by ID
        
        Args:
            lead_id: ID of lead to retrieve
        
        Returns:
            Lead dict, or None if not found
        """
        leads = self._read_leads()
        for lead in leads:
            if lead.get("id") == lead_id:
                return lead
        return None
    
    def get_all_leads(self, sort_by: str = "created_at", reverse: bool = True) -> List[Dict]:
        """
        Get all leads, sorted by field
        
        Args:
            sort_by: Field to sort by (default: created_at)
            reverse: Sort descending if True (default: True)
        
        Returns:
            List of leads sorted by created_at (newest first) by default
        """
        leads = self._read_leads()
        
        try:
            # Sort by specified field
            leads.sort(
                key=lambda x: x.get(sort_by, ""),
                reverse=reverse
            )
        except Exception as e:
            print(f"Error sorting leads: {e}")
        
        return leads
    
    def delete_lead(self, lead_id: str) -> bool:
        """
        Delete a lead by ID
        
        Args:
            lead_id: ID of lead to delete
        
        Returns:
            True if deleted, False if not found
        """
        leads = self._read_leads()
        original_count = len(leads)
        
        leads = [lead for lead in leads if lead.get("id") != lead_id]
        
        if len(leads) < original_count:
            self._write_leads(leads)
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """
        Get pipeline statistics
        
        Returns:
            {
                total: int,
                researched: int,
                sent: int,
                opened: int,
                replied: int,
                by_status: { status -> count }
            }
        """
        leads = self._read_leads()
        
        stats = {
            "total": len(leads),
            "researched": 0,
            "sent": 0,
            "opened": 0,
            "replied": 0,
            "by_status": {}
        }
        
        for lead in leads:
            status = lead.get("status", "researched")
            
            # Count by status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Count main statuses
            if status == "researched":
                stats["researched"] += 1
            elif status == "sent":
                stats["sent"] += 1
            elif status == "opened":
                stats["opened"] += 1
            elif status == "replied":
                stats["replied"] += 1
        
        return stats
    
    def search_leads(self, query: str, fields: List[str] = None) -> List[Dict]:
        """
        Search leads by text in specified fields
        
        Args:
            query: Search text (case-insensitive)
            fields: Fields to search in (default: ["business_name", "city", "industry", "service"])
        
        Returns:
            List of matching leads
        """
        if fields is None:
            fields = ["business_name", "city", "industry", "service"]
        
        leads = self._read_leads()
        query_lower = query.lower()
        results = []
        
        for lead in leads:
            for field in fields:
                value = str(lead.get(field, "")).lower()
                if query_lower in value:
                    results.append(lead)
                    break
        
        return results
    
    def get_leads_by_status(self, status: str) -> List[Dict]:
        """
        Get all leads with a specific status
        
        Args:
            status: Status to filter by
        
        Returns:
            List of leads with that status
        """
        leads = self._read_leads()
        return [lead for lead in leads if lead.get("status") == status]
    
    def export_csv(self, output_path: str = "data/leads.csv") -> bool:
        """
        Export leads to CSV file
        
        Args:
            output_path: Path to write CSV file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import csv
            
            leads = self._read_leads()
            
            if not leads:
                return False
            
            # Ensure directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Get all possible field names
            fieldnames = set()
            for lead in leads:
                fieldnames.update(lead.keys())
            fieldnames = sorted(list(fieldnames))
            
            # Write CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(leads)
            
            return True
        
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False
