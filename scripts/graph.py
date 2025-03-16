import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 构造 DataFrame
data = {
    "Method": ["gpt-4o-mini", "gpt-4o-mini", "gpt-4o", "gpt-4o"],
    "Tool": ["\tool-2", "Localintel", "\tool-2", "Localintel"],
    "Ragas": [0.93, 0.91, 0.93, 0.92],
    "GEval": [None, None, None, None],  # 无数据列
    "BertSc-F1": [0.67, 0.67, 0.66, 0.66]
}

df = pd.DataFrame(data)

# 处理 GEval 缺失数据（填充为 0）
df.fillna(0, inplace=True)

# 设置 X 轴的分组
x_labels = df["Method"] + " (" + df["Tool"] + ")"
x = np.arange(len(x_labels))  # X 轴索引
width = 0.3  # 柱状图宽度

# 绘制柱状图
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - width, df["Ragas"], width, label="Ragas", color='blue')
ax.bar(x, df["GEval"], width, label="GEval", color='green')
ax.bar(x + width, df["BertSc-F1"], width, label="BertSc-F1", color='red')

# 设置 X 轴
ax.set_xticks(x)
ax.set_xticklabels(x_labels, rotation=30, ha="right")
ax.set_ylabel("Score")
ax.set_title("Comparison of Ragas, GEval, and BertSc-F1")
ax.legend()

plt.tight_layout()
plt.show()