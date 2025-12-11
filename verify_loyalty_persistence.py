from app import create_app, db
from app.models import SiteSettings

app = create_app()

with app.app_context():
    print("--- Verifying Loyalty Settings Persistence ---")
    
    # Get settings
    settings = SiteSettings.get_settings()
    print(f"Current Threshold: {settings.loyalty_points_threshold}")
    
    # Update threshold
    new_threshold = 15
    print(f"Updating to: {new_threshold}")
    settings.loyalty_points_threshold = new_threshold
    db.session.commit()
    
    # Re-fetch
    settings = SiteSettings.query.first()
    print(f"Fetched Threshold: {settings.loyalty_points_threshold}")
    
    if settings.loyalty_points_threshold == new_threshold:
        print("SUCCESS: Settings persisted correctly.")
    else:
        print("FAILURE: Settings not persisted.")
        
    # Reset to default
    settings.loyalty_points_threshold = 10
    db.session.commit()
    print("Reset to default (10).")
