import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt

from free_params import FreeParamRegistry, sketch_independent

class GeometryAestheticsEvaluator:
    def __init__(self, points, lines, canvas_size=None, weights=None, circles=None):
        """
        :param points: dict, {point_name: np.array([x, y])} 
                       注意：这里传入的是字典，方便根据名字查找连接关系
        :param lines: list of tuples, [('A', 'B'), ('B', 'C')]
        :param canvas_size: tuple, (width, height)
        :param weights: dict, 权重配置
        """
        self.points = points
        self.lines = lines
        self.circles = circles or []

        self.canvas_bounds = self._infer_canvas_bounds()
        # canvas_bounds: 覆盖所有几何元素的最小矩形，用于计算loss，和最终绘制的图像大小无关
        if canvas_size is None or canvas_size == 'auto':
            self.canvas_w = max(self.canvas_bounds[1] - self.canvas_bounds[0], 1e-9)
            self.canvas_h = max(self.canvas_bounds[3] - self.canvas_bounds[2], 1e-9)
        else:
            self.canvas_w, self.canvas_h = canvas_size
        
        # 提取坐标数组 (N, 2) 用于矩阵运算
        self.coords_arr = np.array(list(points.values()))
        self.point_names = list(points.keys())
        
        # 默认权重
        self.weights = {
            'repulsion': 0.2,  # 斥力权重
            'angle': 0.5,      # 角度分辨率权重
            'aspect': 0.15,    # 扁平/比例权重
            'boundary': 1.0,   # 边界惩罚权重
            'uniformity': 0.2  # 均匀度权重
        }
        if weights:
            self.weights.update(weights)

        # 预计算邻接关系： { 'B': ['A', 'C'] } 表示 B点连接了 A和C
        self._adjacency = self._build_adjacency()

    def _clamp_loss(self, value, min_value=0.1, max_value=1e9):
        return float(np.clip(value, min_value, max_value))

    def _build_adjacency(self):
        adj = {name: [] for name in self.points.keys()}
        for p1, p2 in self.lines:
            if p1 in adj and p2 in adj:
                adj[p1].append(p2)
                adj[p2].append(p1)
        return adj

    def _infer_canvas_bounds(self):
        if len(self.points) == 0 and len(self.circles) == 0:
            return (0.0, 1.0, 0.0, 1.0)

        xs = []
        ys = []
        if len(self.points) > 0:
            coords = np.array(list(self.points.values()))
            xs.extend(coords[:, 0].tolist())
            ys.extend(coords[:, 1].tolist())

        for cx, cy, r in self.circles:
            xs.extend([cx - r, cx + r])
            ys.extend([cy - r, cy + r])

        if len(xs) == 0 or len(ys) == 0:
            return (0.0, 1.0, 0.0, 1.0)

        min_x = float(np.min(xs))
        max_x = float(np.max(xs))
        min_y = float(np.min(ys))
        max_y = float(np.max(ys))

        if abs(max_x - min_x) < 1e-9:
            max_x = min_x + 1e-9
        if abs(max_y - min_y) < 1e-9:
            max_y = min_y + 1e-9

        return (min_x, max_x, min_y, max_y)

    def loss_repulsion(self, min_dist=0.25):
        """
        [斥力场] 防止点与点之间过于拥挤
        采用静电势能模型: loss = sum(1 / distance^2)
        """
        if len(self.coords_arr) < 2: return self._clamp_loss(0.0)

        # 1. 计算两两距离矩阵 (利用广播机制)
        # coords_arr shape: (N, 2)
        # diff shape: (N, N, 2)
        diff = self.coords_arr[:, np.newaxis, :] - self.coords_arr[np.newaxis, :, :]
        dist_sq = np.sum(diff**2, axis=-1) # (N, N)
        
        # 2. 获取上三角部分的距离 (即不重复计算 A-B 和 B-A，且排除 A-A)
        # k=1 表示不包含对角线
        mask = np.triu(np.ones(dist_sq.shape, dtype=bool), k=1)
        distances = np.sqrt(dist_sq[mask])
        
        min_xy = np.min(self.coords_arr, axis=0)
        max_xy = np.max(self.coords_arr, axis=0)
        point_w = max(max_xy[0] - min_xy[0], 1e-9)
        point_h = max(max_xy[1] - min_xy[1], 1e-9)
        distances = distances / max(point_w, point_h)
        
        # 3. 计算 Loss
        # 加上 epsilon 防止除以 0
        epsilon = 1e-5 
        
        # 基础斥力：距离越远，loss 越小
        repulsion_energy = np.sum(1.0 / (distances + epsilon))
        
        # 惩罚项：如果距离小于阈值，施加额外的指数惩罚 (Soft Constraint)
        # 这里的 mask 筛选出所有过近的点对
        too_close_mask = distances < min_dist
        # penalty = np.sum(np.exp(2.0 * (min_dist - distances[too_close_mask])))
        if np.any(too_close_mask):
            penalty = np.sum(np.exp(36.84 * (min_dist - distances[too_close_mask]))) 
            # 36.84 = ln(100)/0.125，期望单个线段恰好为图片长宽中更大者1/4时开始惩罚，1/8时获得100.00的惩罚
        else:
            penalty = 0.0
        
        return self._clamp_loss(repulsion_energy + penalty)

    def loss_angular_resolution(self, min_angle_deg=20.0):
        """
        [角度分辨率] 防止共顶点的线段夹角过小 (锐角惩罚)
        """
        loss = 0.0
        min_angle_rad = np.radians(min_angle_deg)
        # 遍历每个点作为"中心点" (Vertex)
        for center_name, neighbors in self._adjacency.items():
            if len(neighbors) < 2:
                continue
            
            center_pos = self.points[center_name]
            
            # 获取所有连接到该中心点的向量
            # vectors shape: (K, 2)
            vecs = []
            for n_name in neighbors:
                v = self.points[n_name] - center_pos
                norm = np.linalg.norm(v)
                if norm < 1e-6: 
                    # 如果两点重合，向量为0，跳过或给予巨大惩罚
                    vecs.append(np.array([0.0, 0.0])) 
                else:
                    vecs.append(v / norm) # 归一化
            
            vecs = np.array(vecs)
            
            # 两两计算夹角
            # 这里 K 通常很小 (2~4)，双重循环开销可忽略
            for i in range(len(vecs)):
                for j in range(i + 1, len(vecs)):
                    v1 = vecs[i]
                    v2 = vecs[j]
                    
                    # 检查零向量
                    if np.linalg.norm(v1) < 1e-6 or np.linalg.norm(v2) < 1e-6:
                        loss += 100.0 # 重合点的惩罚
                        continue

                    # 点积求 cos
                    dot_val = np.dot(v1, v2)
                    # 数值截断防止 acos 出错 (如 1.000000002)
                    dot_val = np.clip(dot_val, -1.0, 1.0) 
                    
                    angle_rad = np.arccos(dot_val)

                    # 0° 的精确角度在图像上可接受，不施加惩罚
                    if angle_rad < 1e-6:
                        continue
                    
                    # 如果角度小于阈值，施加惩罚
                    # 使用 exp((阈值 - 角度)) 使得越接近 0 度惩罚越剧烈
                    if angle_rad < min_angle_rad:
                        loss += np.sum(np.exp(46.05 * (min_angle_rad - angle_rad))) 
                        # 46.05 = ln(100)/0.1，期望单个角度恰好为20.0°时开始惩罚，10°时获得100.00的惩罚
                        # loss += np.exp(15.0 * (min_angle_rad - angle_rad)) - 1.0

        return self._clamp_loss(loss)

    def loss_aspect_ratio_and_scale(self):
        """
        [整体布局] 防止图形过扁 (长条状) 或 缩成一团
        """
        if len(self.coords_arr) == 0:
            return self._clamp_loss(0.0)
        min_x, max_x, min_y, max_y = self.canvas_bounds
        w = max_x - min_x
        h = max_y - min_y
        
        # 1. 比例惩罚 (Aspect Ratio)
        # 避免除以0
        h = max(h, 1e-4) 
        w = max(w, 1e-4)
        
        ratio = w / h
        upper_ok = 2.0
        upper_hard = 3.0
        lower_ok = 1.0 / upper_ok
        lower_hard = 1.0 / upper_hard

        if lower_ok <= ratio <= upper_ok:
            ratio_loss = 0.0
        elif ratio > upper_ok:
            ratio_loss = 100.0 * np.exp(5 * (ratio - upper_hard))
        else:
            ratio_loss = 100.0 * np.exp(5 * (lower_hard - ratio))

        return self._clamp_loss(ratio_loss)

    def loss_boundary(self):
        """
        [边界约束] 软约束：如果点跑出画布，Loss 激增
        """
        loss = 0.0
        margin = 0.05 # 内边距
        
        # x < 0 + margin
        loss += np.sum(np.maximum(0, margin - self.coords_arr[:, 0]))
        # y < 0 + margin
        loss += np.sum(np.maximum(0, margin - self.coords_arr[:, 1]))
        # x > w - margin
        loss += np.sum(np.maximum(0, self.coords_arr[:, 0] - (self.canvas_w - margin)))
        # y > h - margin
        loss += np.sum(np.maximum(0, self.coords_arr[:, 1] - (self.canvas_h - margin)))
        
        # 使用平方增加梯度
        return self._clamp_loss(loss ** 2)

    def loss_uniformity(self):
        if len(self.coords_arr) == 0:
            return self._clamp_loss(0.0)

        loss = 0.0
        min_xy = np.min(self.coords_arr, axis=0)
        max_xy = np.max(self.coords_arr, axis=0)
        point_w = max(max_xy[0] - min_xy[0], 1e-9)
        point_h = max(max_xy[1] - min_xy[1], 1e-9)
        point_area = point_w * point_h

        shape_min_x, shape_max_x, shape_min_y, shape_max_y = self.canvas_bounds
        shape_w = max(shape_max_x - shape_min_x, 1e-9)
        shape_h = max(shape_max_y - shape_min_y, 1e-9)
        shape_area = shape_w * shape_h

        ratio = point_area / shape_area

        loss = 100.0 * np.exp(60 * (1/2 - ratio))
        # 期望比例低于0.6时开始惩罚，0.5时获得100.00的惩罚

        return self._clamp_loss(loss)

    def compute_total_loss(self):
        """
        计算加权总 Loss
        """
        l_repulsion = self.loss_repulsion()
        l_angle = self.loss_angular_resolution()
        l_aspect = self.loss_aspect_ratio_and_scale()
        l_boundary = self.loss_boundary()
        l_uniformity = self.loss_uniformity()
        
        total = (self.weights['repulsion'] * l_repulsion +
             self.weights['angle'] * l_angle +
             self.weights['aspect'] * l_aspect +
             self.weights['boundary'] * l_boundary +
             self.weights['uniformity'] * l_uniformity)
        
        return total

# ==========================================
# 1. 外部几何引擎 (The "Engine")
# ==========================================
def _lines_for_construction(construction_name, names):
    if len(names) == 2:
        return [(names[0], names[1])]
    if len(names) == 3:
        return [(names[0], names[1]), (names[1], names[2]), (names[2], names[0])]
    if len(names) == 4:
        return [
            (names[0], names[1]),
            (names[1], names[2]),
            (names[2], names[3]),
            (names[3], names[0]),
        ]
    return []


def draw_coor(free_params, construction_name='triangle'):
    """
    外部接口：参数 -> 坐标 + 拓扑结构
    """
    points = sketch_independent(construction_name, list(free_params))
    names = ['A', 'B', 'C', 'D'][:len(points)]

    coords = {n: np.array([p.x, p.y]) for n, p in zip(names, points)}
    lines = _lines_for_construction(construction_name, names)
    return coords, lines

# ==========================================
# 2. 通用布局优化器 (The "Optimizer")
# ==========================================
class GeometricLayoutOptimizer:
    def __init__(self, geometry_func, loss_func, canvas_size='auto'):
        """
        geometry_func: 回调函数，签名需为 func(params) -> (coords, lines)
        loss_func:     回调函数，签名需为 func(coords, lines, canvas_size) -> float
        """
        self.geometry_func = geometry_func 
        self.loss_func = loss_func
        self.canvas_size = canvas_size

    def objective_wrapper(self, params):
        """
        这是传给 scipy.minimize 的包装函数。
        它串联了：参数 -> 几何构造 -> 美学评估
        """
        # 1. 调用外部引擎：参数 -> 几何图形
        result = self.geometry_func(params)
        if len(result) == 3:
            coords, lines, circles = result
            return self.loss_func(coords, lines, self.canvas_size, circles)
        coords, lines = result
        return self.loss_func(coords, lines, self.canvas_size)

    def optimize(self, initial_free_params, bounds=None, options=None):
        print("Starting Optimization...")
        initial_result = self.geometry_func(initial_free_params)
        if len(initial_result) == 3:
            initial_coords, initial_lines, circles = initial_result
            initial_loss = self.loss_func(initial_coords, initial_lines, self.canvas_size, circles)
        else:
            initial_coords, initial_lines = initial_result
            initial_loss = self.loss_func(initial_coords, initial_lines, self.canvas_size)
        print(f"Initial Loss: {initial_loss:.4f}")
        
        if bounds is None:
            # 动态设置边界 (假设所有自由点都在画布内)
            num_params = len(initial_free_params)
            if self.canvas_size is None or self.canvas_size == 'auto':
                max_canvas = 1.0
            else:
                max_canvas = max(self.canvas_size)
            bounds = [(0, max_canvas)] * num_params
        
        if options is None:
            options = {'disp': True, 'maxiter': 500}

        result = minimize(
            fun=self.objective_wrapper,
            x0=initial_free_params,
            method='L-BFGS-B',
            bounds=bounds,
            options=options,
        )
        
        # 使用优化后的参数再次构建图形，以便返回结果
        final_result = self.geometry_func(result.x)
        if len(final_result) == 3:
            final_coords, final_lines, circles = final_result
            final_loss = self.loss_func(final_coords, final_lines, self.canvas_size, circles)
        else:
            final_coords, final_lines = final_result
            final_loss = self.loss_func(final_coords, final_lines, self.canvas_size)
        print(f"Final Loss: {final_loss:.4f}")

        if final_loss > initial_loss:
            return initial_coords, initial_lines, initial_loss, result
        return final_coords, final_lines, final_loss, result

# ==========================================
# 3. 定义美学评价标准 (The "Critic")
# ==========================================
def aesthetic_rules(coords, lines, canvas_size, circles=None):
    """
    计算图形好不好看。
    这个函数现在独立出来了，可以根据需求替换不同的审美标准。
    """
# def updated_aesthetic_rules(coords, lines, canvas_size):
    """
    为了适配 Optimizer 的接口签名 func(coords, lines, canvas_size) -> float
    我们把 Evaluator 包装一下
    """
    evaluator = GeometryAestheticsEvaluator(coords, lines, canvas_size, circles=circles)
    return evaluator.compute_total_loss()