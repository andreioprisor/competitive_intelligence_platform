from db_models import Base
from database import engine

def create_tables():
    """Create all tables in the database"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully!")
    
    # Print table names
    print("\nCreated tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

def drop_tables():
    """Drop all tables (use with caution!)"""
    print("WARNING: Dropping all tables...")
    response = input("Are you sure? Type 'yes' to confirm: ")
    if response.lower() == 'yes':
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped!")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_tables()
    else:
        create_tables()