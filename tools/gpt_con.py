from openai import OpenAI

class GPTReply:
    def __init__(self, model, client="openai"):
        self.model = model
        self.client = client
        self.total_input_tokens = 0  # 记录总输入 token 数
        self.total_output_tokens = 0  # 记录总输出 token 数
        self.total_cost = 0.0  # 记录总费用

        # 定义 GPT-4o mini 的价格（单位：美元）
        self.pricing = {
            "input": 2.50 / 1_000_000,  # 输入 token 价格
            "cached_input": 1.25 / 1_000_000,  # 缓存输入 token 价格
            "output": 10 / 1_000_000,  # 输出 token 价格
        }

    def getreply(self, systemprompt, user1prompt, user2prompt):
        while True:
            try:
                client = OpenAI()

                if user2prompt == "":
                    completion = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": systemprompt},
                            {"role": "user", "content": user1prompt},
                        ],
                        temperature=0.7
                    )
                else:
                    completion = client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": systemprompt},
                            {"role": "user", "content": user1prompt},
                            {"role": "user", "content": user2prompt}
                        ],
                        temperature=0.7
                    )

                # 获取输入和输出的 token 数
                input_tokens = completion.usage.prompt_tokens
                output_tokens = completion.usage.completion_tokens

                # 累加输入和输出的 token 数
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens

                # 计算本次请求的费用并累加
                cost = self._calculate_cost(input_tokens, output_tokens)
                self.total_cost += cost

                return completion.choices[0].message.content

            except Exception as e:
                print(str(e))
                if "maximum context length is" in str(e):
                    return False
                if "Range of input length should" in str(e) or "Exceeded limit on max byt" in str(e):
                    return False
                pass

    def _calculate_cost(self, input_tokens, output_tokens):
        """根据输入和输出的 token 数计算费用"""
        input_cost = input_tokens * self.pricing["input"]
        output_cost = output_tokens * self.pricing["output"]
        return input_cost + output_cost

    def get_total_tokens(self):
        """返回总输入和输出的 token 数"""
        return self.total_input_tokens, self.total_output_tokens

    def get_total_cost(self):
        """返回总费用"""
        return self.total_cost