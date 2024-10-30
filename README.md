### Run the following commands to get started

```bash
# Create a virtual environment using python3
python3 -m venv venv

# Activate the virtual environment (for Linux/MacOS)
source venv/bin/activate

# Install packages
pip install sqlalchemy psycopg2-binary python-dotenv fastapi uvicorn

# Save all dependencies to requirements.txt
pip freeze > requirements.txt
```


### Docker Useful Commands

1. Remove existing docker-compose (if outdated):
```bash
sudo rm /usr/bin/docker-compose
```

2. Install the latest version of Docker Compose:
```bash
# Download the latest version of Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Create a symbolic link
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
```

3. Verify the installation:
```bash
docker-compose --version
```

4. Check your Docker configuration:
```bash
# Check Docker version
docker version

# Check Docker info
docker info
```

5. Now run your containers for both the backend and the database:
```bash
docker-compose up
```

6. To stop any running containers:
```bash
docker-compose down -v
```

7. To rebuild and start the containers:
```bash
docker-compose up --build
```



### Some Research Notes

According to the FHIR specification, search responses are always returned as a Bundle, and the `entry` array is where the actual matching resources are stored. From [build.fhir.org/search.html](https://build.fhir.org/search.html):

> Search responses are always returned as a Bundle. Search result bundles convey a lot of metadata in addition to any possible results, using the various elements available in the bundle resource.

The `entry` array in the Bundle contains the matching resources, and each entry has a `mode` that indicates why it's included. As explained in the specification:

> Within the results bundle, there are three types of entries that MAY be present, identified by the search mode of the entry: `match`, `include`, or `outcome`.

So when we check `patients_data.get("entry")`, we're verifying that the search returned some matching results (if there are no matches, the `entry` array would be empty or missing).

This is why the code raises a 404 error if no `entry` is found:
```python:app/main.py
if not patients_data.get("entry"):
    raise HTTPException(
        status_code=404,
        detail=f"No patients found for postal code {postal_code}"
    )
```

The structure follows the standard FHIR Bundle format, which looks like:
```json
{
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                // ... patient data ...
            }
        }
    ]
}
```