"""Agent 总纲文章封面：深蓝背景 + 三角循环几何图（LLM→工具→结果）。"""
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "sans-serif"]
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

W, H = 12.8, 7.2  # 1280×720 @ dpi=100
fig, ax = plt.subplots(figsize=(W, H), dpi=100)
ax.set_xlim(0, 12.8); ax.set_ylim(0, 7.2); ax.axis("off")

# 深蓝渐变背景
grad = LinearSegmentedColormap.from_list("bg", ["#0b1220", "#1e3a5f"])
bg = np.linspace(0, 1, 256).reshape(-1, 1)
ax.imshow(bg, extent=[0, 12.8, 0, 7.2], aspect="auto", cmap=grad, zorder=0)

def box(x, y, w, h, fc, ec, title, sub):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.5",
                                fc=fc, ec=ec, lw=3, zorder=2))
    ax.text(x + w/2, y + h*0.68, title, ha="center", va="center",
            fontsize=26, fontweight="bold", color="#1e293b", zorder=3)
    ax.text(x + w/2, y + h*0.30, sub, ha="center", va="center",
            fontsize=14, color="#475569", zorder=3)

# 三角循环：LLM(左上) → 工具(右上) → 结果(下)
box(0.9, 4.9, 4.6, 1.7, "#eff6ff", "#3b82f6", "LLM", "推理 · 决定下一步")
box(7.3, 4.9, 4.6, 1.7, "#fff7ed", "#f97316", "工具", "读文件 · 跑命令")
box(4.1, 1.3, 4.6, 1.7, "#f8fafc", "#334155", "观察", "结果放回对话")

def arrow(x1, y1, x2, y2, color, label, lx, ly):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=28, lw=3.5, color=color, zorder=4))
    ax.text(lx, ly, label, fontsize=15, color=color, ha="center", va="center", zorder=5)

arrow(5.6, 5.75, 7.2, 5.75, "#3b82f6", "tool_use", 6.4, 6.15)
arrow(9.6, 4.85, 9.6, 3.35, "#f97316", "执行", 10.35, 4.10)
arrow(8.6, 2.15, 5.8, 4.35, "#64748b", "messages", 6.4, 2.65)

fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
fig.savefig("source/_posts/技术/Agent 实现原理/cover.jpg", dpi=100, bbox_inches="tight",
            pad_inches=0, facecolor=fig.get_facecolor())
plt.close(fig)
print("cover.jpg saved")
