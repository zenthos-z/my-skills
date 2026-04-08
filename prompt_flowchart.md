flowchart TD
    subgraph input["输入层 / Input Layer"]
        direction LR
        A1["--input 文件路径"]
        A2["--refined-content 提炼内容"]
        A3["--prompt 直接提示词"]
        A4["--var 变量注入"]
        A5["--advanced 高级模式"]
    end

    subgraph decision["模式判断 / Mode Selection"]
        D1{"是否有 --prompt?"}
        D2{"是否有 --refined-content?"}
        D3{"是否开启 --advanced?"}
    end

    subgraph mode1["模式1: 手动模式"]
        M1["直接使用 --prompt 内容"]
    end

    subgraph mode2["模式2: 极简模式+Claude提炼"]
        M2_1["读取模板文件"]
        M2_2["替换 content 占位符"]
        M2_3["输出最终提示词"]
        M2_1 --> M2_2 --> M2_3
    end

    subgraph mode3["模式3: 极简模式（默认）"]
        M3_1["读取源文件内容"]
        M3_2["读取模板文件"]
        M3_3["替换 content 占位符"]
        M3_4["输出最终提示词"]
        M3_1 --> M3_2 --> M3_3 --> M3_4
    end

    subgraph mode4["模式4: 高级模式"]
        M4_1["读取源文件内容"]
        M4_2["读取模板文件"]
        M4_3["解析变量语法"]
        M4_4["注入 --var 参数值"]
        M4_5["条件块渲染"]
        M4_6["输出最终提示词"]
        M4_1 --> M4_2 --> M4_3 --> M4_4 --> M4_5 --> M4_6
    end

    subgraph output["输出层 / Output"]
        O1["调用DMX API"]
        O2["生成图片"]
    end

    A1 --> D1
    A2 --> D2
    A3 --> D1
    A4 --> D3
    A5 --> D3

    D1 -->|"是"| M1
    D1 -->|"否"| D2
    D2 -->|"是"| M2_1
    D2 -->|"否"| D3
    D3 -->|"是"| M4_1
    D3 -->|"否"| M3_1

    M1 --> O1
    M2_3 --> O1
    M3_4 --> O1
    M4_6 --> O1
    O1 --> O2

    style A1 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style A2 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style A3 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style A4 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style A5 fill:#d3f9d8,stroke:#2f9e44,stroke-width:2px
    style D1 fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style D2 fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style D3 fill:#ffe3e3,stroke:#c92a2a,stroke-width:2px
    style M1 fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style M2_1 fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style M2_2 fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style M2_3 fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style M3_1 fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style M3_2 fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style M3_3 fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style M3_4 fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style M4_1 fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style M4_2 fill:#e5dbff,stroke:#5f3dc4,stroke-width:2px
    style M4_3 fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style M4_4 fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style M4_5 fill:#ffe8cc,stroke:#d9480f,stroke-width:2px
    style M4_6 fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
    style O1 fill:#f3d9fa,stroke:#862e9c,stroke-width:2px
    style O2 fill:#c5f6fa,stroke:#0c8599,stroke-width:2px
