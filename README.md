# 高斯光束传输计算器

课题：高斯光束经简单光学系统的传输仿真与光斑质量分析软件设计。

采用 Python 开发。当前处于需求记录、开源调研与产品设计讨论阶段，尚未实现计算内核和 GUI。

- [需求记录](docs/requirements.md)：用户已提出的需求、建议补充参数与验收规划。
- [开源与 Skill 调研](docs/research.md)：来源、源码学习、许可和适用边界。
- [产品设计草案](docs/product-design.md)：拟议界面、计算路线和待讨论事项。
- [产品设计方案 V1.0](docs/product-plan.md)：汇总需求、功能、3D 视觉、架构、开发阶段及验收标准，作为当前完整设计入口。
- [开发过程与能力方法记录](docs/development-log.md)：随每次工作同步更新，积累毕业设计报告所需的过程、工具方法、验证和问题处理证据。

运行当前阶段验证：

```powershell
python -B -m unittest discover -s tests -p "test_*.py" -v
& .\tests\Test-Agents.ps1
git diff --check
```

当前测试仅验证需求文档的完整性、链接和阶段状态；物理正确性、GUI 和打包验证将在实现对应功能时增加。
