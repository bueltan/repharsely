import requests

OLLAMA_URL = "http://localhost:11434/api/chat"

import requests

def rephrasely_method(prompt: str, model: str = 'grammar-translator-llama3.2', stream: bool = False) -> str:
    """
    Translate and improve the given prompt using the specified model.
    
    """
    url = 'http://localhost:11434/api/generate'
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': stream
    }

    if stream:
        response = requests.post(url, json=payload, stream=True)
        output = ''
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8')
                output += data
        return output
    else:
        response = requests.post(url, json=payload)
        return response.json().get('response', '')

if __name__ == '__main__':
    prompt = "Translate: Hola Santiago, ¿cómo estás? Espero que estés bien. Te escribo para pedirte ayuda con el módulo de ic-houdini. Estoy trabajando en la migración a Poetry y, aunque quiero comenzar con los tests, necesito hacerlo funcionar primero. Vi que en algún momento trabajaste en este proyecto, por lo que pensé que tal vez podrías orientarme para hacerlo arrancar.Instale Houdini, pero cuando intenta iniciar ic-houdini, me pide un archivo template y de configuración, y no estoy seguro de cómo crearlos. Si te parece, ¿podríamos conversar mañana cuando tengas un momento? Agradecería mucho tu ayuda. :slightly_smiling_face:"
    response = rephrasely_method(prompt)
    print(response)