"""Application configuration.

Add new services here as they provision OpenSearch.
Set the corresponding env var in each deployment namespace.
"""
import os

SERVICES = [
    {
        'name': 'CAP',
        'url_env': 'CAP_OPENSEARCH_URL',
        'default_url': os.environ.get('OPENSEARCH_PROXY_URL', 'http://localhost:8080'),
        'index': 'cap-analytics*',
        'namespace': 'care-arrangement-plan-dev',
    },
    {
        'name': 'Connecting Services',
        'url_env': 'CS_OPENSEARCH_URL',
        'default_url': '',
        'index': 'cs-analytics*',
        'namespace': 'pfl-connecting-services-dev',
    },
]
