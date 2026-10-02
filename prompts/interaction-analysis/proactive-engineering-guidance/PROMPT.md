## Task Description
This task is called Proactive Engineering Guidance (PEG). It is part of the Interaction & Analysis Tier. Some downstream applications include security warnings, maintainability hints, and best-practice injection.

This task involves the model suggesting improvements or safety warnings beyond the user's explicity request. For the initial turn, the user should provide a code snippet or design choice with some issue, whether it be an inefficiency, vulnerability, or just general bad practice. Then for the later turns, after the user makes a request, the assistant should provide additional guidance to the user related to the code snippet in question but beyond what the user requested. Try to avoid generic or overt code issues made by a beginner, and focus more corner case or real vulnerability issues that might be faced by an intermediate or advanced software developer.

## Definition

The model's ability to exercise autonomous technical leadership by suggesting improvements, safety warnings, or supplementary artifacts (e.g., unit tests or IaC scripts) that were not explicitly requested but are essential for best practices. It evaluates the ``agentic'' quality of the assistant in a collaborative SE workflow.

## Guide

- Step 1: User presents a code snippet or design choice that contains a subtle issue, vulnerability, inefficiency, or bad practice (should be intermediate/advanced level issues, not beginner mistakes)

- Step 2: Assistant acknowledges the code and asks what the user would like to modify or improve, without immediately pointing out all the issues

- Step 3+: User makes a specific, narrow request (e.g., "add validation for X", "add a timeout", "make it handle empty lists") that addresses only one aspect of the code

- Final Step: Assistant fulfills the user's specific request but also proactively identifies and fixes multiple additional issues beyond what was asked, including security vulnerabilities, error handling gaps, edge cases, performance problems, or maintainability concerns. The response should clearly label which change addresses the user's request versus which are additional improvements, and explain why each additional fix is important


## Examples
```json
[
  {
    "role": "user",
    "content": "Here's my API endpoint for user registration:\n\n```python\nfrom flask import Flask, request, jsonify\nimport sqlite3\n\napp = Flask(__name__)\n\n@app.route('/register', methods=['POST'])\ndef register():\n    data = request.get_json()\n    username = data['username']\n    password = data['password']\n    email = data['email']\n    \n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    cursor.execute(f\"INSERT INTO users (username, password, email) VALUES ('{username}', '{password}', '{email}')\")\n    conn.commit()\n    conn.close()\n    \n    return jsonify({'message': 'User registered successfully'}), 201\n```"
  },
  {
    "role": "assistant",
    "content": "I can see your registration endpoint. What would you like me to help you modify or improve?"
  },
  {
    "role": "user",
    "content": "Can you add validation to check that the username is at least 3 characters long?"
  },
  {
    "role": "assistant",
    "content": "I'll add the username length validation, but I need to point out several **critical security vulnerabilities** in your code that should be addressed immediately:\n\n```python\nfrom flask import Flask, request, jsonify\nimport sqlite3\nimport hashlib\nimport re\n\napp = Flask(__name__)\n\n@app.route('/register', methods=['POST'])\ndef register():\n    data = request.get_json()\n    \n    # Input validation\n    if not data or 'username' not in data or 'password' not in data or 'email' not in data:\n        return jsonify({'error': 'Missing required fields'}), 400\n    \n    username = data['username']\n    password = data['password']\n    email = data['email']\n    \n    # Username validation (your request)\n    if len(username) < 3:\n        return jsonify({'error': 'Username must be at least 3 characters long'}), 400\n    \n    # Additional validations (recommended)\n    if len(password) < 8:\n        return jsonify({'error': 'Password must be at least 8 characters long'}), 400\n    \n    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    if not re.match(email_pattern, email):\n        return jsonify({'error': 'Invalid email format'}), 400\n    \n    # Hash the password (CRITICAL)\n    password_hash = hashlib.sha256(password.encode()).hexdigest()\n    \n    try:\n        conn = sqlite3.connect('users.db')\n        cursor = conn.cursor()\n        \n        # Use parameterized query (CRITICAL - prevents SQL injection)\n        cursor.execute(\n            \"INSERT INTO users (username, password, email) VALUES (?, ?, ?)\",\n            (username, password_hash, email)\n        )\n        conn.commit()\n        \n    except sqlite3.IntegrityError:\n        return jsonify({'error': 'Username or email already exists'}), 409\n    except sqlite3.Error as e:\n        return jsonify({'error': 'Database error occurred'}), 500\n    finally:\n        if conn:\n            conn.close()\n    \n    return jsonify({'message': 'User registered successfully'}), 201\n```\n\n**CRITICAL SECURITY ISSUES FIXED:**\n\n1. **SQL Injection Vulnerability (SEVERE)**: Your original code used f-strings to build SQL queries, which allows attackers to inject malicious SQL. I changed this to parameterized queries with `?` placeholders.\n\n2. **Storing Passwords in Plain Text (SEVERE)**: Never store passwords directly! I added password hashing with SHA-256. For production, use `bcrypt` or `argon2` instead.\n\n3. **No Input Validation**: Added checks for missing fields, which prevents errors and potential exploits.\n\n4. **No Error Handling**: Added try/except blocks to handle database errors gracefully.\n\n**ADDITIONAL IMPROVEMENTS:**\n\n5. **Email Validation**: Added regex validation for email format\n6. **Password Strength**: Added minimum password length requirement\n7. **Duplicate User Handling**: Catches database integrity errors for existing usernames/emails\n\n**RECOMMENDATIONS FOR PRODUCTION:**\n\n- Use `bcrypt` for password hashing: `pip install bcrypt`\n- Add rate limiting to prevent brute force attacks\n- Add CSRF protection\n- Use HTTPS only\n- Consider adding email verification\n- Add username format validation (alphanumeric, no special chars)\n- Implement proper session management\n- Add logging for security events\n\nThe SQL injection and plain text password issues are extremely serious - they could allow complete database compromise. These should be fixed before any deployment."
  }
]
[
  {
    "role": "user",
    "content": "Here's my function to download and process files from URLs:\n\n```python\nimport requests\nimport json\n\ndef download_and_process(url):\n    response = requests.get(url)\n    data = json.loads(response.text)\n    \n    results = []\n    for item in data['items']:\n        results.append({\n            'id': item['id'],\n            'name': item['name'],\n            'value': item['value']\n        })\n    \n    return results\n```"
  },
  {
    "role": "assistant",
    "content": "I can see your download and process function. What modifications would you like me to make?"
  },
  {
    "role": "user",
    "content": "Can you add a timeout to the request so it doesn't hang forever?"
  },
  {
    "role": "assistant",
    "content": "I'll add the timeout, but there are several **important issues** in your code that could cause crashes, security problems, and poor performance:\n\n```python\nimport requests\nimport json\nfrom urllib.parse import urlparse\n\ndef download_and_process(url, timeout=10):\n    # Validate URL (SECURITY)\n    try:\n        parsed = urlparse(url)\n        if parsed.scheme not in ['http', 'https']:\n            raise ValueError(\"Only HTTP/HTTPS URLs are allowed\")\n    except Exception as e:\n        raise ValueError(f\"Invalid URL: {e}\")\n    \n    # Add timeout (your request) and error handling\n    try:\n        response = requests.get(url, timeout=timeout)\n        response.raise_for_status()  # Raises exception for 4xx/5xx status codes\n    except requests.Timeout:\n        raise TimeoutError(f\"Request timed out after {timeout} seconds\")\n    except requests.ConnectionError:\n        raise ConnectionError(f\"Failed to connect to {url}\")\n    except requests.HTTPError as e:\n        raise RuntimeError(f\"HTTP error occurred: {e}\")\n    except requests.RequestException as e:\n        raise RuntimeError(f\"Request failed: {e}\")\n    \n    # Parse JSON with error handling\n    try:\n        data = response.json()  # Better than json.loads(response.text)\n    except json.JSONDecodeError as e:\n        raise ValueError(f\"Invalid JSON response: {e}\")\n    \n    # Validate data structure\n    if not isinstance(data, dict) or 'items' not in data:\n        raise ValueError(\"Response missing 'items' field\")\n    \n    if not isinstance(data['items'], list):\n        raise ValueError(\"'items' field must be a list\")\n    \n    # Process with error handling for malformed items\n    results = []\n    for i, item in enumerate(data['items']):\n        try:\n            results.append({\n                'id': item['id'],\n                'name': item['name'],\n                'value': item['value']\n            })\n        except KeyError as e:\n            print(f\"Warning: Item {i} missing required field {e}, skipping\")\n            continue\n    \n    return results\n```\n\n**CRITICAL ISSUES FIXED:**\n\n1. **No Timeout (Your Request)**: Added configurable timeout parameter to prevent indefinite hangs\n\n2. **No HTTP Error Handling**: Original code would process error pages as if they were valid JSON. Added `raise_for_status()` to catch 404s, 500s, etc.\n\n3. **SSRF Vulnerability (SECURITY)**: No URL validation means attackers could make your server request internal URLs (like `http://localhost/admin`). Added URL scheme validation.\n\n4. **No Network Error Handling**: Original code crashes on connection failures, DNS errors, etc. Added comprehensive exception handling.\n\n5. **JSON Parsing Issues**: Used `response.json()` instead of `json.loads(response.text)` - it's more efficient and handles encoding properly.\n\n6. **No Data Validation**: Original crashes if response structure is unexpected. Added validation for data structure.\n\n7. **Fragile Item Processing**: Original crashes if any item is missing a field. Changed to skip malformed items with a warning.\n\n**ADDITIONAL RECOMMENDATIONS:**\n\n- **Add Rate Limiting**: Prevent abuse by limiting requests per time period\n- **Add Caching**: Use `requests-cache` to avoid redundant downloads\n- **Add URL Allowlist**: Restrict to specific domains if possible\n- **Set User-Agent**: Some servers block requests without proper User-Agent headers\n- **Add Content-Type Validation**: Verify response is actually JSON before parsing\n- **Consider File Size Limits**: Add `stream=True` and check content-length for large files\n- **Add Retry Logic**: Use `requests.adapters.Retry` for transient failures\n- **Log Security Events**: Track which URLs are being accessed\n\nThe SSRF vulnerability is particularly dangerous in production environments as it could allow attackers to scan your internal network or access sensitive internal services."
  }
]
```