from openai import OpenAI
client = OpenAI(api_key="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")

models = client.models.list()
for model in models.data:
    print(model.id)
