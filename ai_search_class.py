import azure.ai.search as search
import openai
import psycopg2
from psycopg2.extras import Json
import json

class RAGSession:
    def __init__(self, user_id, search_endpoint, search_key, search_index, openai_api_key, db_config):
        """Initialize a RAG session for a specific user.

        Args:
            user_id (str): Unique identifier for the user, provided by the web app.
            search_endpoint (str): Azure AI Search service endpoint.
            search_key (str): Azure AI Search API key.
            search_index (str): Name of the Azure AI Search index.
            openai_api_key (str): OpenAI API key for generating answers and summaries.
            db_config (dict): Configuration for PostgreSQL database connection.
        """
        # Store user ID for session tracking
        self.user_id = user_id
        
        # Initialize Azure AI Search client
        self.search_client = search.SearchClient(
            endpoint=search_endpoint,
            index_name=search_index,
            credential=search_key
        )
        
        # Set OpenAI API key
        openai.api_key = openai_api_key
        
        # Store database configuration
        self.db_config = db_config
        
        # Load or create session data from database
        self.chat_history, self.context_list = self._get_or_create_session()

    def _get_or_create_session(self):
        """Retrieve or create session data from PostgreSQL database.

        Returns:
            tuple: (chat_history, context_list) loaded from database or initialized as empty lists.
        """
        # Connect to PostgreSQL database
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Query for existing user session
        cursor.execute("SELECT chat_history, context_list FROM user_sessions WHERE user_id = %s", (self.user_id,))
        result = cursor.fetchone()
        
        if result:
            # User exists, return stored chat history and context list
            chat_history, context_list = result
        else:
            # New user, initialize empty history and context
            chat_history = []
            context_list = []
            # Insert new session into database
            cursor.execute(
                "INSERT INTO user_sessions (user_id, chat_history, context_list) VALUES (%s, %s, %s)",
                (self.user_id, Json(chat_history), Json(context_list))
            )
            conn.commit()
        
        # Close database connection
        cursor.close()
        conn.close()
        return chat_history, context_list

    def _update_session(self):
        """Update user session data in PostgreSQL database."""
        # Connect to PostgreSQL database
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Update chat history and context list for the user
        cursor.execute(
            "UPDATE user_sessions SET chat_history = %s, context_list = %s WHERE user_id = %s",
            (Json(self.chat_history), Json(self.context_list), self.user_id)
        )
        conn.commit()
        
        # Close database connection
        cursor.close()
        conn.close()

    def _fetch_context(self, query):
        """Fetch relevant context from Azure AI Search for the given query.

        Args:
            query (str): User's query string.

        Returns:
            str: Combined context from search results.
        """
        # Perform search using Azure AI Search
        results = self.search_client.search(search_text=query)
        # Combine search results into a single context string
        context = "\n".join([result['content'] for result in results])
        return context

    def _summarize_contexts(self):
        """Summarize the context list using OpenAI when it exceeds 5 items.

        Returns:
            str: Summarized context.
        """
        # Combine all contexts into a single string
        combined_context = "\n\n".join(self.context_list)
        # Call OpenAI to generate a summary
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Summarize the following context:\n\n{combined_context}",
            max_tokens=150
        )
        # Extract and return the summary
        summary = response.choices[0].text.strip()
        return summary

    def _generate_answer(self, total_context, user_query):
        """Generate an answer using Azure OpenAI based on context and chat history.

        Args:
            total_context (str): Combined context (previous + current).
            user_query (str): User's current query.

        Returns:
            str: Generated answer.
        """
        # Construct prompt with chat history, context, and query
        prompt = (
            f"Conversation history:\n{self._format_chat_history()}\n\n"
            f"Context:\n{total_context}\n\n"
            f"User query: {user_query}\n\nAssistant:"
        )
        # Call OpenAI to generate answer
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150
        )
        # Extract and return the answer
        answer = response.choices[0].text.strip()
        return answer

    def _format_chat_history(self):
        """Format chat history as a string for inclusion in the prompt.

        Returns:
            str: Formatted chat history.
        """
        # Convert chat history to a string with user and AI messages
        return "\n".join([f"User: {entry['user']}\nAI: {entry['ai']}" for entry in self.chat_history])

    def handle_query(self, user_query):
        """Handle a user query and return a JSON response for the web app.

        Args:
            user_query (str): User's query string.

        Returns:
            dict: JSON response with user_id, query, answer, status, and optional error message.
        """
        try:
            # Fetch context for the current query
            current_context = self._fetch_context(user_query)
            
            # Prepare total context
            if len(self.context_list) > 5:
                # Summarize context list if it exceeds 5 items
                summary = self._summarize_contexts()
                total_context = summary + "\n\n" + current_context
                self.context_list = [summary]  # Reset context list with summary
            else:
                # Combine previous and current contexts
                total_context = "\n\n".join(self.context_list + [current_context])
            
            # Generate answer
            answer = self._generate_answer(total_context, user_query)
            
            # Update chat history with query and answer
            self.chat_history.append({"user": user_query, "ai": answer})
            # Append current context to context list
            self.context_list.append(current_context)
            
            # Save updated session to database
            self._update_session()
            
            # Return successful JSON response
            return {
                "user_id": self.user_id,
                "query": user_query,
                "answer": answer,
                "status": "success"
            }
        except Exception as e:
            # Return error response if an exception occurs
            return {
                "user_id": self.user_id,
                "query": user_query,
                "answer": None,
                "status": "error",
                "error_message": str(e)
            }

# Example usage for testing
if __name__ == "__main__":
    # Configuration for Azure AI Search, OpenAI, and PostgreSQL
    search_endpoint = "YOUR_SEARCH_ENDPOINT"
    search_key = "YOUR_SEARCH_KEY"
    search_index = "YOUR_INDEX_NAME"
    openai_api_key = "YOUR_OPENAI_API_KEY"
    db_config = {
        "dbname": "YOUR_DB_NAME",
        "user": "YOUR_DB_USER",
        "password": "YOUR_DB_PASSWORD",
        "host": "YOUR_DB_HOST",
        "port": "5432"
    }

    # Simulate User 1
    user1_session = RAGSession("user123", search_endpoint, search_key, search_index, openai_api_key, db_config)
    response1 = user1_session.handle_query("What is the capital of France?")
    print(json.dumps(response1, indent=2))
    
    # Simulate User 2
    user2_session = RAGSession("user456", search_endpoint, search_key, search_index, openai_api_key, db_config)
    response2 = user2_session.handle_query("What is the capital of Germany?")
    print(json.dumps(response2, indent=2))
    
    # Follow-up query for User 1
    response3 = user1_session.handle_query("What is its population?")
    print(json.dumps(response3, indent=2))