import json
from urllib import request, error
import logging
import ssl
import certifi


def send_webhook(url, payload, api_key=None, api_key_header='Authorization'):
    """Sends a POST request and returns a tuple (success, message)."""
    if not url:
        msg = "Webhook URL is not set."
        logging.warning(msg)
        return False, msg

    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        data = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'CombinedProcessorApp/1.0'
        }

        if api_key:
            # If the header is 'Authorization', assume Bearer token format.
            # Otherwise, use the key directly.
            headers[api_key_header] = f'Bearer {api_key}' if api_key_header == 'Authorization' else api_key

        # Log the request details for debugging purposes
        logging.debug(f"--- Webhook Request ---")
        logging.debug(f"URL: {url}")
        logging.debug(f"Method: POST")
        logging.debug(f"Headers: {headers}")
        logging.debug(f"Payload: {json.dumps(payload)}")
        logging.debug(f"-----------------------")

        req = request.Request(url, data=data, headers=headers, method='POST')
        with request.urlopen(req, context=ssl_context, timeout=10) as response:
            if 200 <= response.status < 300:
                msg = f"Webhook sent successfully to {url} (auth: {'yes' if api_key else 'no'})"
                logging.info(msg)
                return True, "Webhook sent successfully."
            else:
                response_body = response.read().decode()
                msg = f"Webhook failed with status {response.status}: {response_body}"
                logging.warning(msg)
                return False, msg
    except (error.URLError, error.HTTPError, TimeoutError) as e:
        msg = f"Error sending webhook to {url}: {e}"
        logging.error(msg)
        return False, msg