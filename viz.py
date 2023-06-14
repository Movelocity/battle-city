from graphviz import Digraph


def create_resblock_node(dot, prefix, in_dim, hid_dim, hid_layers):
    label = f'ResBlock\nin_dim: {in_dim}\nhid_dim: {hid_dim}\nhid_layers: {hid_layers}'
    dot.node(prefix, label, shape='box', style='filled', color='lightgreen')


def create_collapsed_model_graph(dpi=300):
    dot = Digraph()
    dot.attr(rankdir='LR', dpi=f"{dpi}")  # Left to right orientation and set dpi

    dot.node('input', 'state_size', shape='box', style='filled', color='lightblue')
    dot.node('l1', '512', shape='box', style='filled', color='lightblue')
    dot.edge('input', 'l1')

    create_resblock_node(dot, 'res1', 512, 256, 2)
    dot.edge('l1', 'res1')

    dot.node('l2', '256', shape='box', style='filled', color='lightblue')
    dot.edge('res1', 'l2')

    dot.node('bn1', 'BatchNorm1d', shape='ellipse', style='filled', color='orange')
    dot.edge('l2', 'bn1')

    create_resblock_node(dot, 'res2', 256, 256, 2)
    dot.edge('bn1', 'res2')

    dot.node('dropout', 'Dropout', shape='ellipse', style='filled', color='orange')
    dot.edge('res2', 'dropout')

    create_resblock_node(dot, 'res3', 256, 256, 2)
    dot.edge('dropout', 'res3')

    dot.node('l3', '128', shape='box', style='filled', color='lightblue')
    dot.edge('res3', 'l3')

    dot.node('bn2', 'BatchNorm1d', shape='ellipse', style='filled', color='orange')
    dot.edge('l3', 'bn2')

    create_resblock_node(dot, 'res4', 128, 128, 4)
    dot.edge('bn2', 'res4')

    create_resblock_node(dot, 'res5', 128, 128, 4)
    dot.edge('res4', 'res5')

    dot.node('l4', 'action_size', shape='box', style='filled', color='lightblue')
    dot.edge('res5', 'l4')

    return dot


collapsed_model_graph = create_collapsed_model_graph(dpi=300)
collapsed_model_graph.render('collapsed_q_network', format='png', cleanup=True)


# import torch
# import torch.nn as nn
# import torch.nn.functional as F

# from torchsummary import summary

# from model import QNetwork

# state_size = 1377
# q_network = QNetwork(state_size, action_size=6)
# q_network.eval()

# x = torch.randn(1, state_size)
# output = q_network(x)

# 使用 torchviz 生成有向图并保存为 PDF 文件
# from torchviz import make_dot
# graph = make_dot(output, params=dict(q_network.named_parameters()))
# graph.render("q_network_visualization", format="pdf")

# 获取模型摘要
# summary(q_network, (state_size,))