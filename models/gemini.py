from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",
    temperature=0.1,
    max_output_tokens=1000,
    timeout=30
)