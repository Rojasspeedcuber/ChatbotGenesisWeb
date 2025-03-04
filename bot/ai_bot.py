import os
from decouple import config
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

# Configura as chaves de API
os.environ['GROQ_API_KEY'] = config('GROQ_API_KEY')
os.environ['HUGGINGFACE_API_KEY'] = config('HUGGINGFACE_API_KEY')


class AIBot:
    """
    Classe que representa um assistente de IA especializado no treinamento Django Master.
    """

    def __init__(self):
        """
        Inicializa o bot de IA com um modelo e um mecanismo de recuperação de documentos.
        """
        self.__chat = ChatGroq(model='llama-3.3-70b-versatile')
        self.__retriever = self.__build_retriever()

    def __build_retriever(self):
        """
        Configura o mecanismo de recuperação de documentos com armazenamento vetorial.
        """
        persist_directory = '/app/chroma_data'
        embedding = HuggingFaceEmbeddings()
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding,
        )
        return vector_store.as_retriever(search_kwargs={'k': 30})

    def __build_messages(self, history_messages, question):
        """
        Constrói a lista de mensagens para o contexto da conversa.

        :param history_messages: Histórico de mensagens (lista de dicionários).
        :param question: Pergunta atual do usuário.
        :return: Lista de mensagens formatadas.
        """
        messages = []
        for message in history_messages:
            message_class = HumanMessage if message.get(
                'fromMe') else AIMessage
            messages.append(message_class(content=message.get('body')))
        messages.append(HumanMessage(content=question))
        return messages

    def invoke(self, history_messages, question):
        SYSTEM_TEMPLATE = '''
        Responda as perguntas dos usuários com base perguntas sobre a bíblia abaixo.
        Você é um chatbot especializado na Bíblia Sagrada, capaz de responder perguntas sobre seu conteúdo, interpretação e contexto histórico, cultural e espiritual.
        Seu objetivo é fornecer respostas claras, precisas e baseadas nas escrituras, respeitando todas as tradições cristãs
        Responda de forma natural, agradável e respeitosa. Seja objetivo nas respostas, com 
        informações claras e diretas. Foque em ser natural e humanizado, como um diálogo comum 
        entre duas pessoas.
        Use como base a Bíblia Sagrada em suas principais traduções (ex.: Almeida Revista e Atualizada, NVI, King James, NTLH, etc.)
        Formato de Resposta:
           - Comece citando as passagens bíblicas relevantes (capítulo e versículo).
           - Ofereça uma explicação clara e objetiva.
        Funções Específicas:
            Referências Bíblicas:
            Localize e cite passagens bíblicas relacionadas à pergunta do usuário. 
                Exemplo:
                    Usuário pergunta: "O que a Bíblia diz sobre perdão?"
                    Resposta: "A Bíblia fala sobre perdão em várias passagens, como em Mateus 6:14-15: 
                    'Porque, se perdoardes aos homens as suas ofensas, também vosso Pai celestial vos perdoará. 
                    Se, porém, não perdoardes aos homens as suas ofensas, tampouco vosso Pai perdoará as vossas ofensas.
                    ' Isso enfatiza a importância do perdão no relacionamento com Deus e com o próximo."
            Conselhos Espirituais:
                Responda perguntas de forma prática e espiritual, sempre baseada na Bíblia.
                Exemplo: 
                    Usuário pergunta: "Como lidar com a ansiedade à luz da Bíblia?"
                    Resposta: "A Bíblia oferece consolo em Filipenses 4:6-7: 'Não andeis ansiosos por coisa alguma; antes, em tudo, sejam os vossos pedidos conhecidos diante de Deus pela oração e súplicas com ação de graças. E a paz de Deus, que excede todo entendimento, guardará os vossos corações e as vossas mentes em Cristo Jesus.'"


        Leve em consideração também o histórico de mensagens da conversa com o usuário.
        Responda sempre em português brasileiro.

        <context>
        {context}
        </context>
        '''

        # Recupera os documentos relacionados à pergunta
        docs = self.__retriever.invoke(question)

        # Configura o prompt para o modelo
        question_answering_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', SYSTEM_TEMPLATE),
                MessagesPlaceholder(variable_name='messages'),

            ]
        )

        # Cria o pipeline de processamento de documentos e respostas
        document_chain = create_stuff_documents_chain(
            self.__chat, question_answering_prompt)

        # Gera a resposta com base no contexto e no histórico
        response = document_chain.invoke({
            'context': docs,
            'messages': self.__build_messages(history_messages, question),
        })
        return response
