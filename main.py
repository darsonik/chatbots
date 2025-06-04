from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain

import os
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(
    base_url="https://api.kluster.ai/v1",
    api_key=os.getenv("KLUSTER_API_KEY"), # Replace with your actual API key
    model="mistralai/Mistral-Nemo-Instruct-2407",
)

# Initialize memory and chat history
# message_history is required in the provided code because it serves as the storage backend for the conversation history managed by ConversationBufferMemory
message_history = ChatMessageHistory()
memory = ConversationBufferMemory(
    chat_memory=message_history,
    return_messages=True,
    human_prefix = "human",
    ai_prefix = "system",
    memory_key = "history"
)

# Define a prompt template - include a system instruction for the assistant, a placeholder for the conversation history, and an input slot for the user's query
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

#Create the ConversationChain - pass in the LLM, memory, and this prompt template so every new user query is automatically enriched with the stored conversation context and guided by the assistant's role
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    prompt=prompt
)
# Example conversation loop

# Send the first user prompt
question1 = "Hello! Can you tell me something interesting about the city of Kathmandu?"
print("Question 1:", question1)
response1 = conversation.predict(input=question1)
print("Response 1:", response1)

# Send a follow-up question referencing previous context
question2 = "What is the population of that city?"
print("\nQuestion 2:", question2)
response2 = conversation.predict(input=question2)
print("Response 2:", response2)