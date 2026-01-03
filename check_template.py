#!/usr/bin/env python3
"""
Script to check email template content in the database.
Usage: python check_template.py <template_id>
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.db.models.email_template import EmailTemplate

def check_template(template_id: int):
    """Check template content."""
    db = SessionLocal()
    try:
        template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        
        if not template:
            print(f"❌ Template with ID {template_id} not found!")
            return
        
        print(f"\n{'='*80}")
        print(f"📧 EMAIL TEMPLATE - ID: {template.id}")
        print(f"{'='*80}\n")
        print(f"Name: {template.name}")
        print(f"Category: {template.category}")
        print(f"Type: {template.type}")
        print(f"Org ID: {template.org_id}")
        print(f"Master Template ID: {template.master_template_id}")
        print(f"\nSubject:")
        print(f"  {template.subject}")
        print(f"\nBody ({len(template.body) if template.body else 0} characters):")
        print(f"  {template.body[:500] if template.body else '(empty)'}")
        if template.body and len(template.body) > 500:
            print(f"  ... (truncated, total {len(template.body)} chars)")
        print(f"\nVariables: {template.variables}")
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_template.py <template_id>")
        print("Example: python check_template.py 1")
        sys.exit(1)
    
    try:
        template_id = int(sys.argv[1])
        check_template(template_id)
    except ValueError:
        print("❌ Template ID must be a number")
        sys.exit(1)


