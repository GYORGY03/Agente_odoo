from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.1,
    max_tokens=1000,
    timeout=30
    # ... (other params)
)