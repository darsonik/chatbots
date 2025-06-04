import azure.ai.search as search
import openai

# Initialize Azure AI Search and OpenAI clients (replace with your credentials)
search_client = search.SearchClient(endpoint="YOUR_SEARCH_ENDPOINT", index_name="YOUR_INDEX_NAME", credential="YOUR_SEARCH_KEY")
openai.api_key = "YOUR_OPENAI_API_KEY"

# Initialize chat history and context list
chat_history = []
context_list = []

def fetch_context(query):
    # Fetch context from Azure AI Search based on the query
    results = search_client.search(search_text=query)
    context = "\n".join([result['content'] for result in results])
    return context

def summarize_contexts(context_list):
    # Combine contexts and summarize using OpenAI
    combined_context = "\n\n".join(context_list)
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Summarize the following context:\n\n{combined_context}",
        max_tokens=150
    )
    summary = response.choices[0].text.strip()
    return summary

def generate_answer(total_context, user_query):
    # Generate answer using Azure OpenAI with the total context and query
    prompt = f"Conversation history:\n{format_chat_history()}\n\nContext:\n{total_context}\n\nUser query: {user_query}\n\nAssistant:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    answer = response.choices[0].text.strip()
    return answer

def format_chat_history():
    # Format chat history as a string
    return "\n".join([f"User: {entry['user']}\nAI: {entry['ai']}" for entry in chat_history])

def handle_query(user_query):
    global context_list, chat_history
    
    # Fetch current context from Azure AI Search
    current_context = fetch_context(user_query)
    
    # Prepare total context
    if len(context_list) > 5:
        # Summarize context list if it exceeds 5 items
        summary = summarize_contexts(context_list)
        total_context = summary + "\n\n" + current_context
        context_list = [summary]  # Reset context list with summary
    else:
        # Use all previous contexts plus current context
        total_context = "\n\n".join(context_list + [current_context])
    
    # Generate answer
    answer = generate_answer(total_context, user_query)
    
    # Update chat history
    chat_history.append({"user": user_query, "ai": answer})
    
    # Update context list
    context_list.append(current_context)
    
    return answer

# Example usage
if __name__ == "__main__":
    # Initial query
    query1 = "What is the capital of France?"
    answer1 = handle_query(query1)
    print(f"User: {query1}\nAI: {answer1}\n")
    
    # Follow-up query
    query2 = "What is its population?"
    answer2 = handle_query(query2)
    print(f"User: {query2}\nAI: {answer2}\n")