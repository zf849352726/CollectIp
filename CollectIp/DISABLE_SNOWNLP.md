# 禁用SnowNLP指南

此文档说明如何在CollectIp项目中禁用SnowNLP，以解决内存受限环境下的问题。

## 为什么要禁用SnowNLP？

SnowNLP是一个中文自然语言处理库，用于情感分析和文本处理。然而，它在初始化时需要加载大量的模型数据到内存中，这在内存受限的环境下（如小型VPS服务器）可能导致:

1. `MemoryError` 异常
2. 进程被操作系统的OOM Killer终止（退出代码-9）
3. Django命令如`check`、`migrate`等无法正常运行

## 已应用的解决方案

我们已经修改了`index/text_utils.py`文件，通过以下方式禁用了SnowNLP：

1. 注释掉SnowNLP的导入语句：`# from snownlp import SnowNLP`
2. 用基于简单词典的情感分析方法替代SnowNLP的情感分析

这种方法保持了API的兼容性，同时大大减少了内存使用。

## 如何在不同环境间切换

### 在生产环境（内存受限）

保持当前的设置，使用基于词典的简单情感分析。

### 在开发环境（内存充足）

如果您想在开发环境中使用完整的SnowNLP功能，请恢复`index/text_utils.py`文件：

1. 取消注释导入语句：`from snownlp import SnowNLP`
2. 恢复原始的`analyze_sentiment`方法实现，使用SnowNLP进行分析

您可以在`index/text_utils.py`文件中找到被注释掉的原始SnowNLP代码。

## 对功能的影响

禁用SnowNLP后，主要影响以下功能：

1. **情感分析**：精度会降低，因为简单词典不如预训练模型准确
2. **摘要生成**：不受影响，因为它使用jieba而不是SnowNLP
3. **关键词提取**：不受影响，因为它使用jieba而不是SnowNLP

## 性能考量

- 禁用SnowNLP后，内存使用量大幅降低（约减少200-300MB）
- 情感分析的速度可能会提高，因为词典匹配通常比模型推理快
- Django命令（如`check`、`makemigrations`、`migrate`等）可以在内存受限环境下正常运行

## 如何测试修改是否有效

您可以运行以下命令来测试禁用SnowNLP后是否能成功运行Django命令：

```bash
cd /usr/local/CollectIp/CollectIp
python test_django_check.py
```

如果您仍然遇到内存问题，可以尝试增加内存限制：

```bash
python run_with_memory_limit.py --memory-limit 500 check
```

## 长期解决方案

如果您希望长期同时兼容内存受限环境和高精度情感分析，可以考虑：

1. 实现一个独立的情感分析微服务，使用更多内存在单独的服务器上运行
2. 使用环境变量或配置文件在不同环境间动态选择情感分析实现方式
3. 探索更轻量级的情感分析库或预训练好的较小模型

## 恢复原始功能

如果您需要完全恢复SnowNLP功能，请参考`index/text_utils_backup.py`（如果存在）或在项目的Git历史中找到原始版本。 