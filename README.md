# AI RAG Application with Azure AI Search and OpenAI

This project implements a Retrieval-Augmented Generation (RAG) application using Azure AI Search and Azure OpenAI. It supports multiple users by managing user-specific chat histories and contexts in an Azure PostgreSQL database. The `RAGSession` class encapsulates the logic for handling queries, fetching contexts, summarizing contexts when they exceed 5 items, and generating answers. The application is designed to integrate with a web app, receiving a `user_id` and returning JSON responses.

## Features

- **Multi-User Support**: Each user's session is isolated using a unique `user_id`, with data stored in Azure PostgreSQL.
- **Context Management**: Fetches context from Azure AI Search and summarizes it using OpenAI when the context list exceeds 5 items.
- **Chat History**: Maintains conversation history per user to support follow-up questions.
- **JSON Responses**: Returns structured responses for web app integration.
- **Error Handling**: Includes try-except blocks to handle database or API errors gracefully.

## Prerequisites

- **Python 3.8+**
- **Azure PostgreSQL Database** with a `user_sessions` table (schema provided below).
- **Azure AI Search** service with an index containing searchable content.
- **Azure OpenAI** account with access to the `text-davinci-003` model (or equivalent).
- **Dependencies**:
  - `psycopg2-binary`
  - `azure-ai-search`
  - `openai`

Install dependencies using:

```bash
pip install psycopg2-binary azure-ai-search openai
```

## Database Setup

Create a `user_sessions` table in your Azure PostgreSQL database to store user data:

```sql
CREATE TABLE user_sessions (
    user_id VARCHAR(255) PRIMARY KEY,
    chat_history JSONB,
    context_list JSONB
);
```

- `user_id`: Unique identifier for the user (provided by the web app).
- `chat_history`: JSON array of conversation history (e.g., \`\[{"user": "query", "ai": "response"}\]').
- `context_list`: JSON array of contexts fetched from Azure AI Search.

## Configuration

Update the following placeholders in `rag_session_class.py` with your actual credentials:

- **Azure AI Search**:

  - `YOUR_SEARCH_ENDPOINT`: Your Azure AI Search service endpoint.
  - `YOUR_SEARCH_KEY`: Your Azure AI Search API key.
  - `YOUR_INDEX_NAME`: Name of the search index.

- **Azure OpenAI**:

  - `YOUR_OPENAI_API_KEY`: Your OpenAI API key.

- **Azure PostgreSQL**:

  - `YOUR_DB_NAME`: Database name.
  - `YOUR_DB_USER`: Database user.
  - `YOUR_DB_PASSWORD`: Database password.
  - `YOUR_DB_HOST`: Database host (e.g., `yourserver.postgres.database.azure.com`).
  - `YOUR_DB_PORT`: Database port (default: `5432`).

Example configuration in the code:

```python
search_endpoint = "https://your-search-service.search.windows.net"
search_key = "your-search-api-key"
search_index = "your-index-name"
openai_api_key = "your-openai-api-key"
db_config = {
    "dbname": "your-db-name",
    "user": "your-db-user",
    "password": "your-db-password",
    "host": "your-db-host",
    "port": "5432"
}
```

## Usage

The `RAGSession` class handles a single user's session, managing chat history and contexts. Here's how to use it:

1. **Instantiate a Session**: Create a `RAGSession` instance for a user with their `user_id`:

   ```python
   user_session = RAGSession(
       user_id="user123",
       search_endpoint=search_endpoint,
       search_key=search_key,
       search_index=search_index,
       openai_api_key=openai_api_key,
       db_config=db_config
   )
   ```

2. **Handle Queries**: Call `handle_query` to process a user query and get a JSON response:

   ```python
   response = user_session.handle_query("What is the capital of France?")
   print(json.dumps(response, indent=2))
   ```

3. **Example Output**:

   ```json
   {
     "user_id": "user123",
     "query": "What is the capital of France?",
     "answer": "The capital of France is Paris.",
     "status": "success"
   }
   ```

4. **Web App Integration**: Use a web framework like FastAPI to create an API endpoint:

   ```python
   from fastapi import FastAPI
   app = FastAPI()
   sessions = {}  # Cache RAGSession instances
   
   @app.post("/query")
   async def query_endpoint(request: dict):
       user_id = request.get("user_id")
       user_query = request.get("query")
       if user_id not in sessions:
           sessions[user_id] = RAGSession(user_id, search_endpoint, search_key, search_index, openai_api_key, db_config)
       return sessions[user_id].handle_query(user_query)
   ```

   The web app sends a POST request with `user_id` and `query`, receiving a JSON response with the answer.

## Example Workflow

1. **User 1 Query**:

   - Query: "What is the capital of France?"
   - Response: `{"user_id": "user123", "query": "What is the capital of France?", "answer": "The capital of France is Paris.", "status": "success"}`
   - Context and chat history are saved to PostgreSQL.

2. **User 2 Query**:

   - Query: "What is the capital of Germany?"
   - Response: `{"user_id": "user456", "query": "What is the capital of Germany?", "answer": "The capital of Germany is Berlin.", "status": "success"}`
   - Separate session data is stored for User 2.

3. **User 1 Follow-Up**:

   - Query: "What is its population?"
   - Response: `{"user_id": "user123", "query": "What is its population?", "answer": "The population of Paris is approximately 2.1 million.", "status": "success"}`
   - Uses User 1’s previous context and history for context-aware response.

## Context Summarization

- The application stores up to 5 contexts per user in the `context_list`.
- When `context_list` exceeds 5 items, it is summarized using OpenAI’s `text-davinci-003` model, and the summary replaces the previous contexts.
- This ensures efficient handling of follow-up questions while keeping context manageable.

## Production Considerations

- **Connection Pooling**: Use `psycopg2.pool` or `SQLAlchemy` for efficient database connection management.

- **Session Expiry**: Add a `last_updated` column to the `user_sessions` table and implement a cleanup job to remove inactive sessions (e.g., after 24 hours).

  ALTER TABLE user_sessions ADD COLUMN last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

  Update the `_update_session` method to set `last_updated`:

  ```python
  cursor.execute(
      "UPDATE user_sessions SET chat_history = %s, context_list = %s, last_updated = CURRENT_TIMESTAMP WHERE user_id = %s",
      (Json(self.chat_history), Json(self.context_list), self.user_id)
  )
  ```

- **Security**:

  - Validate `user_id` to prevent injection attacks (though `psycopg2` parameterizes queries).
  - Use authentication to verify `user_id` corresponds to an authorized user.

- **Scalability**:

  - Deploy on Azure App Service or Azure Functions with a load balancer.
  - Use Azure PostgreSQL read replicas for read-heavy workloads.

- **Error Handling**: The `handle_query` method includes try-except blocks to return error details in the JSON response.

## Troubleshooting

- **Database Connection Errors**: Verify `db_config` credentials and ensure the Azure PostgreSQL database is accessible.
- **Azure AI Search Errors**: Check `search_endpoint`, `search_key`, and `search_index` for correctness.
- **OpenAI Errors**: Ensure `openai_api_key` is valid and the `text-davinci-003` model is available.
- **No Context Returned**: Confirm that the Azure AI Search index contains relevant data for the queries.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For questions or support, contact the development team at \[your-email@example.com\].