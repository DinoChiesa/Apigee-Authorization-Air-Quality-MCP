## Setting up Auth0 as OIDC provider

Auth0 offers a Free Plan for testing OIDC.

For use within an MCP scenario, I suggest this:

### Setup Steps

1. Signup and Sign-in to Auth0.

3. In the Left-hand-side Navigation bar, select Applications.

2. After you have signed in you should see the "Getting Started" page:
   ![Getting Started](./images/Auth0-getting-started.png)

   If not, Visit [Manage](https://manage.auth0.com/)

4. Create an Application
   - Name: MCP-Client-App1 (or whatever seems appropriate)
   - Client ID and Secret are auto-populated
   - The Domain will be auto-populated too.
   - Take note of all three items, you will need these later.
   - scroll down, find the OAuthV2 callback text box. 
     - For Gemini CLI, add http://localhost:7777/oauth/callback
     - For ADK-built agents, add http://localhost:8000/dev-ui/   
     - Exact match is required. The trailing slash is important after dev-ui.
   - set `ID Token Expiry` if you like. I chose 3600.
   - **Save**

5. In the Left-hand-side Navigation bar, select APIs

6. Create an API. This is a protected "thing".

   - Name: "MCP Products Service"
   - Identifier (=Audience): air-quality-oauth
   - (optional) set AccessToken expiry: 86400
   - **Save**


9. Add a User, and set Groups on the user entity:

   - Navigate to User Management > Users
   - Create User
   - Supply an email and password
   - Click the User to modify settings
   - Scroll down to "App Metadata"
   - Supply this value:
     ```json
     {
       "groups": [ "staff", "prodmgmt", "users" ]
     }
     ```
   - **Save**


9. Modify your MCP Client settings appropriately.

   If you are using Gemini CLI, then modify `settings.json` to look like this:

   ```json
    "mcpServers": {
      "products": {
        "httpUrl": "https://your-apigee-hostname/mcp-access-control/mcp",
        "oauth": {
          "enabled": true,
          "audiences": ["air-quality-oauth"],
          "clientId": "client-id-from-Auth0",
          "clientSecret": "client-secret-from-auth0"
        }
      }
    },
   ```

8. In your terminal or `.env` file, set the `OIDC_SERVER` environment variable to
   `https:\\` plus the Domain from the Auth0 setup dashboard.

   It will look something like this: https://dev-b08ghq9d2n1am5pl.us.auth0.com/

   You will use this later when you deploy proxies to Apigee.
