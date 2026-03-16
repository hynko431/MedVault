import yaml
import os
import sys

def validate_capabilities():
    file_path = os.path.join("docker", "model_capabilities.yaml")
    print(f"--- Validating: {file_path} ---")
    
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found at {file_path}")
        sys.exit(1)
        
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            
        if not data:
            print("❌ ERROR: File is empty")
            sys.exit(1)
            
        print("✅ SUCCESS: YAML syntax is valid")
        
        # Check for expected root keys
        required_keys = ['capabilities', 'profiles']
        missing = [k for k in required_keys if k not in data]
        
        if missing:
            print(f"⚠️ WARNING: Missing expected root keys: {missing}")
        else:
            print(f"✅ SUCCESS: Registry structure is intact")
            
        print("\nRegistered Capabilities:")
        for cap in data.get('capabilities', {}):
            print(f" - {cap}")
            
    except Exception as e:
        print(f"❌ ERROR: Failed to parse YAML: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_capabilities()
