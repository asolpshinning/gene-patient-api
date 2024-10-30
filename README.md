### Run the following commands to get started

```bash
# Create a virtual environment using python3
python3 -m venv venv

# Activate the virtual environment (for Linux/MacOS)
source venv/bin/activate

# Install packages
pip install sqlalchemy psycopg2-binary python-dotenv

# Save all dependencies to requirements.txt
pip freeze > requirements.txt
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