# import_csv.py - UPDATED WITH CORRECT COLUMN NAMES
import pandas as pd
import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import ZuluEnglishPair

def import_csv_data():
    """One-time script to import CSV data"""
    
    # File path to your CSV
    csv_file_path = r"C:\Users\mthok\isuzu_corpus__backend\data\corpus.csv"
    
    # Check if file exists
    if not os.path.exists(csv_file_path):
        print(f"❌ File not found: {csv_file_path}")
        return
    
    print(f"📁 Reading CSV file: {csv_file_path}")
    
    try:
        # Read CSV file
        df = pd.read_csv(csv_file_path)
        print(f"✅ CSV loaded successfully. Shape: {df.shape}")
        print(f"📊 Columns: {list(df.columns)}")
        
        # ✅ FIXED: Use lowercase column names
        print("\n📋 Sample data:")
        print(df[['isizulu', 'english']].head(3))
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # ✅ FIXED: Use lowercase column names
    df_clean = df[['isizulu', 'english']].dropna()
    df_clean = df_clean[df_clean['isizulu'].str.strip() != '']
    df_clean = df_clean[df_clean['english'].str.strip() != '']
    
    print(f"\n🔢 After cleaning: {len(df_clean)} rows")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check existing count
        existing_count = ZuluEnglishPair.query.count()
        print(f"📊 Existing records in database: {existing_count}")
        
        # Ask for confirmation
        if existing_count > 0:
            response = input(f"\n⚠️  Database already has {existing_count} records. Continue importing? (y/n): ")
            if response.lower() != 'y':
                print("❌ Import cancelled.")
                return
        
        # Import data
        batch_size = 10000
        imported_count = 0
        skipped_count = 0
        total_batches = (len(df_clean) + batch_size - 1) // batch_size
        
        print(f"\n🔄 Starting import of {len(df_clean)} rows in {total_batches} batches...")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, len(df_clean))
            batch = df_clean.iloc[start_idx:end_idx]
            
            print(f"📦 Processing batch {batch_num + 1}/{total_batches} (rows {start_idx}-{end_idx})")
            
            for _, row in batch.iterrows():
                # ✅ FIXED: Use lowercase column names and correct model field names
                isizulu_text = row['isizulu'].strip()
                english_text = row['english'].strip()
                
                # Check if this pair already exists
                existing = ZuluEnglishPair.query.filter_by(
                    isiZulu=isizulu_text,  # Model field name (capital Z)
                    English=english_text   # Model field name (capital E)
                ).first()
                
                if not existing:
                    new_pair = ZuluEnglishPair(
                        isiZulu=isizulu_text,  # Model field name (capital Z)
                        English=english_text   # Model field name (capital E)
                    )
                    db.session.add(new_pair)
                    imported_count += 1
                else:
                    skipped_count += 1
            
            # Commit after each batch
            db.session.commit()
            print(f"✅ Batch {batch_num + 1} completed - Imported: {imported_count}, Skipped: {skipped_count}")
        
        # Final stats
        final_count = ZuluEnglishPair.query.count()
        print(f"\n🎉 Import completed successfully!")
        print(f"📊 Final statistics:")
        print(f"   • Newly imported: {imported_count}")
        print(f"   • Skipped (duplicates): {skipped_count}")
        print(f"   • Total in database: {final_count}")

if __name__ == "__main__":
    import_csv_data()