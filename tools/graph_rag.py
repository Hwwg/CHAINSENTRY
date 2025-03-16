from typing import List
from langchain.docstore.document import Document

from langchain_core.runnables import  RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import StrOutputParser
import os
from langchain_community.graphs import Neo4jGraph
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_experimental.graph_transformers import LLMGraphTransformer
from neo4j import GraphDatabase
from yfiles_jupyter_graphs import GraphWidget
from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores.neo4j_vector import remove_lucene_chars

from dotenv import load_dotenv


class Entities(BaseModel):
    """Identifying information about entities."""

    names: List[str] = Field(
        description="All the person, organization, or business entities that appear in the text "
    )


class Graph_rag():
    def __init__(self,module):
        '''

        :param module: 用于将document转化为graph text的基座模型以及后续问答处理的模型，目前就将两个都设为gpt-4o-mini，效果比较好
        '''
        load_dotenv()
        self.graph = Neo4jGraph()
        self.llm = self.llm_init(module)
        self.entity_chain = self.entity_chain_generation()
        self.vector_retriever = self.vector_index_gen()

    def llm_init(self,module):
        llm_type = module
        if llm_type == "ollama":
            llm = ChatOllama(model="llama3.1", temperature=0)
        else:
            llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")

        return llm

    def word_split(self, data):
        # 检查传入的是文件路径还是字符串
        if os.path.isfile(data):
            # 如果是文件路径，使用 TextLoader 读取文件内容
            loader = TextLoader(file_path=data)
            docs = loader.load()
        else:
            # 如果是直接的字符串内容，创建 Document 对象列表
            docs = [Document(page_content=data)]

        # 使用文本分割器处理内容
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=24)
        documents = text_splitter.split_documents(docs)

        return documents

    def document_to_graph_text(self, documents, document_label):
        '''
        将documents导入到neo4j中，基于document_label区分不同批次的数据
        :param documents: 文档数据
        :param document_label: 用于区分不同批次数据的标签
        :return:
        '''
        try:
            llm_transformer = LLMGraphTransformer(llm=self.llm)

            # Extract graph data
            graph_documents = llm_transformer.convert_to_graph_documents(documents)

            # Store to neo4j
            self.graph.add_graph_documents(
                graph_documents,
                baseEntityLabel=True,
                include_source=True,
                document_label=document_label
            )

            # 创建索引以提高查询效率
            self.graph.query(
                f"CREATE FULLTEXT INDEX entity_{document_label} IF NOT EXISTS FOR (e:__Entity__{document_label}) ON EACH [e.id]")

            # 初始化向量检索
            # print(type(self.vector_index_gen))  # 查看 self.vector_index_gen 是否为函数

            self.vector_retriever = self.vector_index_gen()

            return True
        except Exception as e:
            return False

    def vector_index_gen(self):
        vector_index = Neo4jVector.from_existing_graph(
            OpenAIEmbeddings(),
            search_type="hybrid",
            node_label="Document",
            text_node_properties=["text"],
            embedding_node_property="embedding"
        )
        vector_retriever = vector_index.as_retriever()
        return vector_retriever

    def entity_chain_generation(self):
        class Entities(BaseModel):
            """Identifying information about entities."""

            names: list[str] = Field(
                ...,
                description="All the entities that appear in the text",
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "As a professional Security Operations Engineer, your job is to handle, extract, and analyze the entities required for tracing data in alert incidents.",
                ),
                (
                    "human",
                    "Use the given format to extract information from the following"
                    "input: {question}",
                ),
            ]
        )

        entity_chain = prompt | self.llm.with_structured_output(Entities)
        return entity_chain

    def generate_full_text_query(self,input: str) -> str:
        """
        Generate a full-text search query for a given input string.

        This function constructs a query string suitable for a full-text
        search. It processes the input string by splitting it into words and
        appending a similarity threshold (~2 changed characters) to each
        word, then combines them using the AND operator. Useful for mapping
        entities from user questions to database values, and allows for some
        misspelings.
        """
        full_text_query = ""
        words = [el for el in remove_lucene_chars(input).split() if el]
        for word in words[:-1]:
            full_text_query += f" {word}~2 AND"
        full_text_query += f" {words[-1]}~2"
        return full_text_query.strip()

    # Fulltext index query
    def graph_retriever(self, question: str, document_label: str) -> str:
        """
        Collects the neighborhood of entities mentioned
        in the question and filters based on document_label
        """
        result = ""
        entities = self.entity_chain.invoke({"question": question})
        for entity in entities.names:
            response = self.graph.query(
                """CALL db.index.fulltext.queryNodes($document_label, $query, 
            {limit:2})
            YIELD node,score
            CALL {
              MATCH (node)-[r:!MENTIONS]->(neighbor)
              RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS 
              output
              UNION
              MATCH (node)<-[r:!MENTIONS]-(neighbor)
              RETURN neighbor.id + ' - ' + type(r) + ' -> ' +  node.id AS 
              output
            }
            RETURN output LIMIT 50
                """,
                {"query": self.generate_full_text_query(entity), "document_label": 'Entity_'+document_label},
            )
            result += "\n".join([el['output'] for el in response])
            # print(result)
        return result

    def full_retriever(self,question: str,document_label):
        graph_data = self.graph_retriever(question,document_label)
        vector_data = [el.page_content for el in self.vector_retriever.invoke(question)]
        final_data = f"""Graph data:
    {graph_data}
    vector data:
    {"#Document ".join(vector_data)}
        """
        return final_data

    def get_answer(self, question, document_label):
        template = """Answer the question based only on the following context:
        {context}

        Question: {question}
        Use natural language and be concise.
        Answer:"""

        prompt = ChatPromptTemplate.from_template(template)

        # Modify full_retriever to accept question and document_label from input
        chain = (
                {
                    "context": lambda input: self.full_retriever(input["question"], input["document_label"]),
                    # Pass both question and document_label
                    "question": RunnablePassthrough(),
                }
                | prompt
                | self.llm
                | StrOutputParser()
        )

        # Pass both question and document_label as input
        result = chain.invoke(input={"question": question, "document_label": document_label})

        return result
#
# neo = Graph_rag("gpt-4o-mini")
# print(neo.get_answer("what about the specific file reputaiton",'5515284'))


