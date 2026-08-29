# 电导率预测迭代

电导专业工作流覆盖 DataCore 大装置电导率预测迭代。推荐使用完整页面 URL 作为 `TARGET`，它同时保留实验、链路和轮次身份。

| 当前阶段 | 常用命令 | 是否写入 |
| --- | --- | --- |
| 定位轮次 | `status` | 否 |
| 生成推荐 | `recommend`、`export` | 是 / 否 |
| 回传实测 | `validate`、`upload` | 否 / 是 |
| 更新模型 | `train`、`retry-fold` | 是 |
| 进入下一轮 | `compare`、`decide`、`next` | 否 / 是 |

## 1. 查看当前状态

```bash
datacore --json conductivity status TARGET
```

以服务端返回的 `nextAction` 为准，不根据页面位置或本地记录猜测下一步。

## 2. 生成并导出本轮推荐

```bash
datacore conductivity recommend TARGET --wait --yes
datacore conductivity export TARGET --format unilab --output task.xls
```

推荐计算使用当前用户在 DataCore 中保存的 Bohrium 凭据和项目号。CLI 不接受命令行 AccessKey，也不会退回平台自带凭据。

## 3. 校验并上传实测结果

```bash
datacore conductivity validate TARGET measured.csv
datacore conductivity upload TARGET measured.csv --yes
```

`validate` 只读；`upload` 会在服务端再次校验，并按推荐编号把 UniLab 回传值与本轮推荐配方关联。默认顺便合并训练数据，只有明确需要时才使用 `--no-merge`。

## 4. 五折训练

```bash
datacore conductivity train TARGET --wait --yes
```

状态查询会分别显示五折。若某一折失败，只重试未完成的折：

```bash
datacore conductivity retry-fold TARGET --fold 3 --yes
```

服务端保留已经完成的折，不重复提交。

## 5. 比较、决策和下一轮

```bash
datacore conductivity compare TARGET
datacore conductivity decide TARGET continue --reason "继续优化" --yes
datacore conductivity next TARGET --yes
```

`next` 使用链路尾部冻结的配置，不接受 Agent 临时生成的实验参数。

## 长任务

`--wait` 只是本地观察。关闭终端、断网或本地超时不会取消云端工作；再次执行 `status` 即可继续跟踪。

遇到 Bohrium、数据校验或单折失败，请按[故障恢复](/troubleshooting/)处理，不要绕过服务端给出的 `nextAction`。
