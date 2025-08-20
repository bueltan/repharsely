import requests


if __name__ == "__main__":
    from rephrasely.src.grok_llm_rephrasely import rephrasely_method

    prompt = (
        "Translate: Hola Santiago, ¿cómo estás? Espero que estés bien. "
        "Te escribo para pedirte ayuda con el módulo de ic-houdini. Estoy trabajando en la migración a Poetry y, "
        "aunque quiero comenzar con los tests, necesito hacerlo funcionar primero. "
        "Vi que en algún momento trabajaste en este proyecto, por lo que pensé que tal vez podrías orientarme "
        "para hacerlo arrancar. Instale Houdini, pero cuando intenta iniciar ic-houdini, me pide un archivo "
        "template y de configuración, y no estoy seguro de cómo crearlos. "
        "Si te parece, ¿podríamos conversar mañana cuando tengas un momento? "
        "Agradecería mucho tu ayuda. :slightly_smiling_face:"
    )
    # Set the API key as an environment variable in CMD before running:
    # set XAI_API_KEY=xai-xxxx
    try:
        # Non-streaming
        result = rephrasely_method(prompt, model="grok-3-latest", stream=False)
        print("\n\n--- RESULT ---\n", result)
    except requests.HTTPError as e:
        print(f"Error: {e}")

    # Or streaming
    # print("\n--- STREAM ---")
    # result = translate_and_improve(prompt, model="grok", stream=True)