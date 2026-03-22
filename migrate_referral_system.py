"""
Migration script for Referral & Rewards System
Run this script once to:
1. Add new columns to User and SiteSettings tables
2. Create ReferralRecord and InfluencerCode tables
3. Generate referral codes for all existing users

Usage: python migrate_referral_system.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, SiteSettings

app = create_app()

with app.app_context():
    print("🔄 Starting Referral System Migration...")
    
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    
    # --- User table columns ---
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    
    if 'referral_code' not in user_columns:
        # SQLite doesn't support ADD COLUMN with UNIQUE, so add without constraint first
        db.session.execute(text('ALTER TABLE user ADD COLUMN referral_code VARCHAR(10)'))
        db.session.commit()
        # Then create a unique index separately
        db.session.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_user_referral_code ON user(referral_code)'))
        db.session.commit()
        print("  ✅ Added 'referral_code' column to User table")
    else:
        print("  ⏭️ 'referral_code' column already exists")
    
    if 'referred_by' not in user_columns:
        db.session.execute(text('ALTER TABLE user ADD COLUMN referred_by INTEGER REFERENCES user(id)'))
        db.session.commit()
        print("  ✅ Added 'referred_by' column to User table")
    else:
        print("  ⏭️ 'referred_by' column already exists")
    
    # --- SiteSettings table column ---
    settings_columns = [col['name'] for col in inspector.get_columns('site_settings')]
    
    if 'referral_target_count' not in settings_columns:
        db.session.execute(text('ALTER TABLE site_settings ADD COLUMN referral_target_count INTEGER DEFAULT 10'))
        db.session.commit()
        print("  ✅ Added 'referral_target_count' column to SiteSettings table")
    else:
        print("  ⏭️ 'referral_target_count' column already exists")
    
    # --- Create ReferralRecord table ---
    existing_tables = inspector.get_table_names()
    
    if 'referral_record' not in existing_tables:
        db.session.execute(text('''
            CREATE TABLE referral_record (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL REFERENCES user(id),
                referred_user_id INTEGER NOT NULL UNIQUE REFERENCES user(id),
                name_prefix VARCHAR(3),
                first_wash_completed BOOLEAN DEFAULT 0,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        db.session.commit()
        print("  ✅ Created 'referral_record' table")
    else:
        print("  ⏭️ 'referral_record' table already exists")
    
    # --- Create InfluencerCode table ---
    if 'influencer_code' not in existing_tables:
        db.session.execute(text('''
            CREATE TABLE influencer_code (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                completed_washes INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        db.session.commit()
        print("  ✅ Created 'influencer_code' table")
    else:
        print("  ⏭️ 'influencer_code' table already exists")
    
    # Step 2: Generate referral codes for existing users without one
    print("\n🔄 Generating referral codes for existing users...")
    users_without_code = User.query.filter(
        (User.referral_code == None) | (User.referral_code == '')
    ).all()
    
    count = 0
    for user in users_without_code:
        user.referral_code = User.generate_referral_code()
        count += 1
    
    db.session.commit()
    print(f"  ✅ Generated referral codes for {count} users")
    
    # Step 3: Ensure SiteSettings has referral_target_count set
    settings = SiteSettings.get_settings()
    if not settings.referral_target_count:
        settings.referral_target_count = 10
        db.session.commit()
        print("  ✅ Set default referral_target_count to 10")
    
    print("\n🎉 Migration completed successfully!")
