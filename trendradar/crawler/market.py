# coding=utf-8
"""
市场数据抓取模块

使用 AKShare 获取 A 股实时市场数据，注入 AI 分析 prompt 作为额外上下文。
包括：大盘指数、行业板块资金流、概念板块资金流、北向资金。
"""

from typing import Optional


def fetch_market_data() -> str:
    """
    抓取 A 股市场数据，返回格式化字符串供 AI 分析使用。

    如果抓取失败（非交易日、网络问题等），返回空字符串，不影响主流程。

    Returns:
        格式化的市场数据字符串，或空字符串
    """
    try:
        import akshare as ak
    except ImportError:
        print("[市场数据] akshare 未安装，跳过市场数据抓取")
        return ""

    sections = []

    sections.append(_fetch_indices(ak))
    sections.append(_fetch_sector_fund_flow(ak))
    sections.append(_fetch_concept_fund_flow(ak))
    sections.append(_fetch_north_flow(ak))

    result = "\n\n".join(s for s in sections if s)

    if result:
        print("[市场数据] 抓取成功")
    else:
        print("[市场数据] 无可用数据（可能是非交易日或网络问题）")

    return result


def _fetch_indices(ak) -> str:
    """获取主要大盘指数实时行情"""
    try:
        df = ak.stock_zh_index_spot_em(symbol="上证系列指数")
        sh_row = df[df["代码"] == "000001"]
        sh_data = _format_index_row(sh_row, "上证指数") if not sh_row.empty else None
    except Exception:
        sh_data = None

    try:
        df = ak.stock_zh_index_spot_em(symbol="深证系列指数")
        sz_row = df[df["代码"] == "399001"]
        sz_data = _format_index_row(sz_row, "深证成指") if not sz_row.empty else None
        cy_row = df[df["代码"] == "399006"]
        cy_data = _format_index_row(cy_row, "创业板指") if not cy_row.empty else None
    except Exception:
        sz_data = None
        cy_data = None

    lines = ["### 大盘指数"]
    for d in [sh_data, sz_data, cy_data]:
        if d:
            lines.append(d)

    if len(lines) <= 1:
        return ""

    return "\n".join(lines)


def _format_index_row(row, name: str) -> str:
    """格式化单行指数数据"""
    try:
        latest = float(row.iloc[0]["最新价"])
        change_pct = float(row.iloc[0]["涨跌幅"])
        arrow = "↑" if change_pct > 0 else ("↓" if change_pct < 0 else "→")
        return f"- {name}: {latest:.2f} ({arrow}{change_pct:+.2f}%)"
    except Exception:
        return f"- {name}: 数据解析失败"


def _fetch_sector_fund_flow(ak) -> str:
    """获取行业板块资金流（今日，前10流入+前10流出）"""
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
    except Exception as e:
        print(f"[市场数据] 行业资金流获取失败: {e}")
        return ""

    return _format_fund_flow(df, "行业板块资金流（今日）")


def _fetch_concept_fund_flow(ak) -> str:
    """获取概念板块资金流（今日，前10流入+前10流出）"""
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")
    except Exception as e:
        print(f"[市场数据] 概念资金流获取失败: {e}")
        return ""

    return _format_fund_flow(df, "概念板块资金流（今日）")


def _format_fund_flow(df, title: str) -> str:
    """格式化资金流数据：取主力净流入前10和后10"""
    if df is None or df.empty:
        return ""

    fund_col = None
    for col in df.columns:
        if "主力净流入" in col and "净额" in col:
            fund_col = col
            break

    if fund_col is None:
        return ""

    pct_col = None
    for col in df.columns:
        if "今日涨跌幅" in col:
            pct_col = col
            break

    name_col = "名称" if "名称" in df.columns else None
    if name_col is None:
        return ""

    df_sorted = df.sort_values(by=fund_col, ascending=False)

    top10 = df_sorted.head(10)
    bottom10 = df_sorted.tail(10)

    lines = [f"### {title}"]
    lines.append("**资金流入前10:**")
    for _, row in top10.iterrows():
        name = row[name_col]
        flow = float(row[fund_col]) / 1e8
        pct = float(row[pct_col]) if pct_col else 0
        lines.append(f"- {name}: 主力净流入 {flow:+.2f}亿 (涨跌幅{pct:+.2f}%)")

    lines.append("\n**资金流出前10:**")
    for _, row in bottom10.iterrows():
        name = row[name_col]
        flow = float(row[fund_col]) / 1e8
        pct = float(row[pct_col]) if pct_col else 0
        lines.append(f"- {name}: 主力净流出 {flow:+.2f}亿 (涨跌幅{pct:+.2f}%)")

    return "\n".join(lines)


def _fetch_north_flow(ak) -> str:
    """获取北向资金净流入"""
    try:
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df is None or df.empty:
            return ""
    except Exception:
        try:
            df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
            if df is None or df.empty:
                return ""
            latest = df.tail(1).iloc[0]
            value_col = None
            for col in df.columns:
                if "净流入" in col or "金额" in col:
                    value_col = col
                    break
            if value_col is None:
                return ""
            val = float(latest[value_col]) / 1e8
            return f"### 北向资金\n- 今日净流入: {val:+.2f}亿"
        except Exception:
            return ""

    return ""
