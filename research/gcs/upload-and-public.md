# Google Cloud Storage Upload and Public Access

## Installation
```bash
pip install google-cloud-storage
```

## Authentication
```bash
# Set up credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
# OR use gcloud auth
gcloud auth application-default login
```

## Upload and Make Public
```python
from google.cloud import storage

def upload_and_make_public(bucket_name, source_file, destination_name):
    """Upload file and make it publicly accessible."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_name)
    
    # Upload with custom metadata
    blob.upload_from_filename(source_file)
    
    # Make public
    blob.make_public()
    
    # Get public URL
    return blob.public_url
```

## Batch Upload with Metadata
```python
def upload_product_image(bucket_name, image_path, product_title, category):
    """Upload product image with SEO-friendly naming."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # Create SEO-friendly filename
    safe_title = product_title.lower().replace(' ', '-')[:50]
    safe_category = category.lower().replace(' ', '-')
    destination_name = f"products/{safe_category}/{safe_title}.jpg"
    
    blob = bucket.blob(destination_name)
    
    # Set metadata
    blob.metadata = {
        'product_title': product_title,
        'category': category,
        'uploaded_at': datetime.now().isoformat()
    }
    blob.content_type = 'image/jpeg'
    
    # Upload and make public
    blob.upload_from_filename(image_path)
    blob.make_public()
    
    return blob.public_url
```

## Make Entire Bucket Public
```python
def set_bucket_public_iam(bucket_name):
    """Make entire bucket publicly readable."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    policy = bucket.get_iam_policy(requested_policy_version=3)
    policy.bindings.append({
        "role": "roles/storage.objectViewer",
        "members": ["allUsers"]
    })
    
    bucket.set_iam_policy(policy)
```