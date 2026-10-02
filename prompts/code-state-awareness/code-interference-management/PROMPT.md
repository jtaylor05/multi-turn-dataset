## Task Description
This task is called Code Interference Management (CIM). It is part of the Code State Awareness Tier. Some downstream applications include topic shift handling and legacy-vs-current code isolation.

This task involves the model ignoring irrelevant or misleading prior context after a topic shift. This task might begin with the user introducing some codebase related context that the user would use for a turn or more. After the initial stage, the user then shifts topic, changing the context to a different codebase in which they are asking the assistant questions. This would only need to be 1 turn. Try to avoid overlapping contexts between the introduction-context and the topic-shift-context to challenge the assistant.

## Definition

The model's proficiency in selective context suppression, specifically identifying when a domain or topic shift (e.g., from Backend to Frontend) renders previous history obsolete. It evaluates the robustness of the attention mechanism against ``context leakage,'' where legacy or out-of-domain artifacts inappropriately influence current task execution.

## Guide

- Step 1: User introduces initial context (based off of some sort of code-base; APIs, structure, architecture, etc.) for a specific task or framework
- Step 2: Assistant provides a detailed response addressing the initial context, potentially including code examples, explanations, or solutions specific to that context
- Step 3 (Optional): User may ask follow-up question(s) related to the initial context, and assistant continues working within that same framework/environment
- Step 4: User abruptly shifts to a completely different codebase without explicitly stating they're changing contexts
- Final Step: Assistant must recognize the topic shift and respond appropriately to the NEW context, ignoring the previously established setup, constraints, and code patterns from Steps 1-3, even though they were recently discussed

## Examples
```json
[
  {
    "role": "user",
    "content": "I'm building a REST API with Flask and need to add JWT authentication. How should I structure the login endpoint?"
  },
  {
    "role": "assistant",
    "content": "Here's how to create a JWT authentication login endpoint in Flask:\n\n```python\nfrom flask import Flask, request, jsonify\nfrom flask_jwt_extended import JWTManager, create_access_token, create_refresh_token\nfrom werkzeug.security import check_password_hash\nimport sqlite3\n\napp = Flask(__name__)\napp.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this!\njwt = JWTManager(app)\n\n@app.route('/api/login', methods=['POST'])\ndef login():\n    data = request.get_json()\n    \n    if not data or 'username' not in data or 'password' not in data:\n        return jsonify({'error': 'Missing credentials'}), 400\n    \n    username = data['username']\n    password = data['password']\n    \n    # Query user from database\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))\n    user = cursor.fetchone()\n    conn.close()\n    \n    if not user or not check_password_hash(user[2], password):\n        return jsonify({'error': 'Invalid credentials'}), 401\n    \n    # Create tokens\n    access_token = create_access_token(identity=user[0])\n    refresh_token = create_refresh_token(identity=user[0])\n    \n    return jsonify({\n        'access_token': access_token,\n        'refresh_token': refresh_token,\n        'user_id': user[0],\n        'username': user[1]\n    }), 200\n```\n\n**Installation:**\n```bash\npip install flask-jwt-extended\n```\n\n**Configuration in your app:**\n```python\napp.config['JWT_SECRET_KEY'] = 'your-secret-key'\napp.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # 1 hour\napp.config['JWT_REFRESH_TOKEN_EXPIRES'] = 2592000  # 30 days\n```"
  },
  {
    "role": "user",
    "content": "How do I set up middleware to verify tokens in my Express routes?"
  },
  {
    "role": "assistant",
    "content": "In Express (Node.js), you create authentication middleware to verify JWT tokens. Here's how to set it up:\n\n**Install dependencies:**\n```bash\nnpm install jsonwebtoken express\n```\n\n**Create authentication middleware:**\n\n```javascript\nconst jwt = require('jsonwebtoken');\n\nconst JWT_SECRET = 'your-secret-key'; // Use environment variable in production\n\n// Authentication middleware\nconst authenticateToken = (req, res, next) => {\n    const authHeader = req.headers['authorization'];\n    const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN\n    \n    if (!token) {\n        return res.status(401).json({ error: 'Access token required' });\n    }\n    \n    jwt.verify(token, JWT_SECRET, (err, user) => {\n        if (err) {\n            return res.status(403).json({ error: 'Invalid or expired token' });\n        }\n        \n        req.user = user; // Attach user data to request\n        next();\n    });\n};\n\nmodule.exports = { authenticateToken };\n```\n\n**Using the middleware in routes:**\n\n```javascript\nconst express = require('express');\nconst { authenticateToken } = require('./middleware/auth');\n\nconst app = express();\napp.use(express.json());\n\n// Public route - no authentication\napp.post('/api/login', (req, res) => {\n    const { username, password } = req.body;\n    \n    // Validate credentials (simplified)\n    // In production, query database and verify password hash\n    \n    const user = { id: 1, username: username };\n    \n    // Generate token\n    const accessToken = jwt.sign(user, JWT_SECRET, { expiresIn: '1h' });\n    \n    res.json({ accessToken });\n});\n\n// Protected route - requires authentication\napp.get('/api/profile', authenticateToken, (req, res) => {\n    // req.user contains the decoded JWT payload\n    res.json({\n        userId: req.user.id,\n        username: req.user.username\n    });\n});\n\n// Multiple protected routes\napp.get('/api/dashboard', authenticateToken, (req, res) => {\n    res.json({ message: `Welcome ${req.user.username}` });\n});\n\napp.put('/api/settings', authenticateToken, (req, res) => {\n    // Update user settings\n    res.json({ message: 'Settings updated' });\n});\n\napp.listen(3000, () => {\n    console.log('Server running on port 3000');\n});\n```\n\n**Optional: Role-based authorization middleware:**\n\n```javascript\nconst authorizeRole = (roles) => {\n    return (req, res, next) => {\n        if (!req.user || !roles.includes(req.user.role)) {\n            return res.status(403).json({ error: 'Insufficient permissions' });\n        }\n        next();\n    };\n};\n\n// Admin-only route\napp.delete('/api/users/:id', \n    authenticateToken, \n    authorizeRole(['admin']), \n    (req, res) => {\n        // Delete user logic\n        res.json({ message: 'User deleted' });\n    }\n);\n```\n\n**Environment configuration (.env):**\n\n```\nJWT_SECRET=your-very-secure-secret-key\nJWT_EXPIRES_IN=1h\n```\n\nThe middleware extracts the token from the `Authorization` header, verifies it, and attaches the decoded user information to `req.user` for use in your route handlers."
  }
]

[
  {
    "role": "user",
    "content": "I'm using the Stripe API to process payments. How do I create a payment intent?"
  },
  {
    "role": "assistant",
    "content": "Here's how to create a payment intent with the Stripe API:\n\n```python\nimport stripe\n\nstripe.api_key = 'sk_test_your_secret_key'\n\ndef create_payment(amount, currency='usd'):\n    try:\n        payment_intent = stripe.PaymentIntent.create(\n            amount=amount,  # Amount in cents\n            currency=currency,\n            payment_method_types=['card'],\n            metadata={'order_id': '12345'}\n        )\n        \n        return {\n            'client_secret': payment_intent.client_secret,\n            'id': payment_intent.id\n        }\n    except stripe.error.StripeError as e:\n        return {'error': str(e)}\n\n# Example: charge $50.00\nresult = create_payment(5000)\nprint(result['client_secret'])  # Send this to frontend\n```\n\n**Installation:**\n```bash\npip install stripe\n```\n\nThe `client_secret` should be sent to your frontend to complete the payment with Stripe.js."
  },
  {
    "role": "user",
    "content": "How do I send an SMS notification in Twilio when the payment succeeds?"
  },
  {
    "role": "assistant",
    "content": "Here's how to send an SMS notification using the Twilio API:\n\n```python\nfrom twilio.rest import Client\n\naccount_sid = 'your_account_sid'\nauth_token = 'your_auth_token'\nclient = Client(account_sid, auth_token)\n\ndef send_payment_notification(to_phone, amount):\n    try:\n        message = client.messages.create(\n            body=f'Payment of ${amount/100:.2f} received successfully. Thank you!',\n            from_='+1234567890',  # Your Twilio number\n            to=to_phone\n        )\n        \n        return {\n            'sid': message.sid,\n            'status': message.status\n        }\n    except Exception as e:\n        return {'error': str(e)}\n\n# Example usage after payment success\nsend_payment_notification('+19876543210', 5000)\n```\n\n**Installation:**\n```bash\npip install twilio\n```\n\n**Combining with Stripe webhook:**\n\n```python\n@app.route('/webhook', methods=['POST'])\ndef stripe_webhook():\n    payload = request.get_data()\n    event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)\n    \n    if event.type == 'payment_intent.succeeded':\n        payment_intent = event.data.object\n        amount = payment_intent.amount\n        customer_phone = payment_intent.metadata.get('phone')\n        \n        # Send SMS notification\n        send_payment_notification(customer_phone, amount)\n    \n    return jsonify({'status': 'success'})\n```\n\nMake sure to store the customer's phone number in the payment intent metadata when creating it."
  }
]

```