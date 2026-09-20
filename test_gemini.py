from app.ai.gemini import ask_gemini


response = ask_gemini(
    "Réponds simplement : P.R.O.S.P.E.R. est opérationnel."
)

print(response)