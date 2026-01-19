# -*- coding: utf-8 -*-
"""
Micro Controller - Swarm Control Algorithms for Drone Swarm Applications

This module implements actual swarm control algorithms used in real drone systems:
- Potential Field Method: For obstacle avoidance and formation maintenance
- Boids Algorithm: For natural flocking behavior
- Separation, Alignment, Cohesion: Core swarm behaviors

These algorithms are directly applicable to real-world drone swarm control.
"""

import math
from dataclasses import dataclass
from typing import List
from typing import Tuple
from typing import Dict
from typing import Any
from pathlib import Path

# Import spatial partitioning for O(N^2) optimization
try:
    from utils.spatial_partition import OptimizedSpatialPartition
    SPATIAL_PARTITION_AVAILABLE = True
except ImportError:
    SPATIAL_PARTITION_AVAILABLE = False
    OptimizedSpatialPartition = None

# Import K-D Tree for sparse distribution optimization
try:
    from utils.kd_tree import KDTree
    KD_TREE_AVAILABLE = True
except ImportError:
    KD_TREE_AVAILABLE = False
    KDTree = None

try:
    from sc2.position import Point2
    SC2_AVAILABLE = True
except ImportError:
    # Mock types for testing without SC2
    class Point2:
        def __init__(self, coords):
            self.x, self.y = coords[0], coords[1]

        def distance_to(self, other):
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

        def towards(self, other, distance):
            dx = other.x - self.x
            dy = other.y - self.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist == 0:
                return self
            return Point2(
                (self.x + dx / dist * distance,
                 self.y + dy / dist * distance))
    SC2_AVAILABLE = False


# Utility functions to reduce code duplication
def _distance(p1: Point2, p2: Point2) -> float:
    """Calculate Euclidean distance between two points."""


return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


def _magnitude(p: Point2) -> float:
    """Calculate magnitude of a vector."""


return math.sqrt(p.x**2 + p.y**2)


def _normalize(p: Point2, max_magnitude: float = None) -> Point2:
    """Normalize a vector, optionally limiting to max_magnitude."""


mag = _magnitude(p)
if mag == 0:
    pass
return Point2((0.0, 0.0))

if max_magnitude and mag > max_magnitude:
    pass
return Point2((p.x / mag * max_magnitude, p.y / mag * max_magnitude))

return Point2((p.x / mag, p.y / mag))


def _zero_point() -> Point2:
    """Create a zero point."""


return Point2((0.0, 0.0))


def _average_points(points: List[Point2]) -> Point2:
    """Calculate average position of a list of points."""


if not points:
    pass
return _zero_point()
return Point2((
    sum(p.x for p in points) / len(points),
    sum(p.y for p in points) / len(points)
))


@dataclass
class SwarmConfig:
    """Configuration for swarm control algorithms."""


separation_distance: float = 2.0  # Minimum distance between units
alignment_radius: float = 5.0  # Radius for alignment behavior
cohesion_radius: float = 8.0  # Radius for cohesion behavior
separation_weight: float = 1.5  # Weight for separation force
alignment_weight: float = 1.0  # Weight for alignment force
cohesion_weight: float = 1.0  # Weight for cohesion force
obstacle_repulsion: float = 2.0  # Repulsion force from obstacles
max_speed: float = 5.0  # Maximum movement speed
potential_field_strength: float = 10.0  # Strength of potential field


class PotentialFieldController:
    """
Potential Field Method for Swarm Control

This implements the actual potential field algorithm used in:
- Drone swarm obstacle avoidance
- Formation maintenance
- Path planning

The potential field creates attractive forces toward goals
and repulsive forces away from obstacles and other units.
    """


    def __init__(self, config: SwarmConfig = None):
        """Initialize Potential Field Controller."""
        self.config = config or SwarmConfig()

    def calculate_potential_field(
        self,
        unit_position: Point2,
        target_position: Point2,
        nearby_units: List[Point2],
        obstacles: List[Point2] = None
    ) -> Point2:
        """
        Calculate potential field force at unit position.

        Args:
            unit_position: Current position of the unit
            target_position: Target/goal position (attractive)
            nearby_units: Positions of nearby units (repulsive)
            obstacles: Positions of obstacles (repulsive)

        Returns:
            Force vector (Point2) representing desired movement direction
        """
        obstacles = obstacles or []

        # Attractive force toward target (goal)
        to_target = Point2((target_position.x - unit_position.x,
                            target_position.y - unit_position.y))
        target_distance = _magnitude(to_target)

        if target_distance > 0:
            attractive_force = Point2((
                to_target.x / target_distance * self.config.potential_field_strength,
                to_target.y / target_distance * self.config.potential_field_strength
            ))
        else:
            attractive_force = _zero_point()

        # Repulsive force from nearby units (separation)
        repulsive_force = _zero_point()
        for nearby_unit in nearby_units:
            to_unit = Point2((nearby_unit.x - unit_position.x,
                              nearby_unit.y - unit_position.y))
            unit_distance = _magnitude(to_unit)

            if 0 < unit_distance < self.config.separation_distance:
                # Strong repulsion when too close
                repulsion_strength = self.config.obstacle_repulsion / (unit_distance + 0.1)
                repulsive_force = Point2((
                    repulsive_force.x - to_unit.x / unit_distance * repulsion_strength,
                    repulsive_force.y - to_unit.y / unit_distance * repulsion_strength
                ))

        # Repulsive force from obstacles
        for obstacle in obstacles:
            to_obstacle = Point2((obstacle.x - unit_position.x,
                                  obstacle.y - unit_position.y))
            obstacle_distance = _magnitude(to_obstacle)

            if obstacle_distance < self.config.separation_distance * 2:
                repulsion_strength = self.config.obstacle_repulsion / (obstacle_distance + 0.1)
                repulsive_force = Point2((
                    repulsive_force.x - to_obstacle.x / obstacle_distance * repulsion_strength,
                    repulsive_force.y - to_obstacle.y / obstacle_distance * repulsion_strength
                ))

        # Combine forces
        total_force = Point2((
            attractive_force.x + repulsive_force.x,
            attractive_force.y + repulsive_force.y
        ))

        # Limit force magnitude
        return _normalize(total_force, self.config.max_speed)


class BoidsController:
    """
Boids Algorithm for Natural Flocking Behavior

Implements the classic Boids algorithm with three core behaviors:
1. Separation: Steer away from nearby units
2. Alignment: Steer toward average heading of nearby units
3. Cohesion: Steer toward average position of nearby units

This is the same algorithm used in:
- Drone swarm formation flying
- Autonomous vehicle platooning
- Multi-agent coordination systems
    """


def __init__(self, config: SwarmConfig = None, use_kd_tree: bool = False):
        """
        Initialize Boids Controller.
        
        Args:
            config: Swarm configuration
            use_kd_tree: Use K-D Tree instead of Grid (better for sparse distributions)
        """
        self.config = config or SwarmConfig()
        self.use_kd_tree = use_kd_tree
        
        # OPTIMIZATION: Use spatial partitioning for O(N^2) -> O(N) optimization
        # Option 1: K-D Tree (better for sparse distributions, O(N log N))
        if use_kd_tree and KD_TREE_AVAILABLE and KDTree:
            self.kd_tree = KDTree()
            self.spatial_partition = None
            self._use_spatial_partition = False
            self._use_kd_tree = True
        # Option 2: Grid-based (better for dense distributions, O(N))
        elif SPATIAL_PARTITION_AVAILABLE and OptimizedSpatialPartition:
            max_radius = max(
                self.config.separation_distance,
                self.config.cohesion_radius,
                self.config.alignment_radius or 10.0
            )
            cell_size = max_radius * 0.5  # Optimal cell size
            self.spatial_partition = OptimizedSpatialPartition(cell_size=cell_size)
            self.kd_tree = None
            self._use_spatial_partition = True
            self._use_kd_tree = False
        else:
            self.spatial_partition = None
            self.kd_tree = None
            self._use_spatial_partition = False
            self._use_kd_tree = False


    def calculate_boids_velocity(
        self,
        unit_position: Point2,
        unit_velocity: Point2,
        nearby_units: List[Tuple[Point2, Point2]] = None,  # (position, velocity)
        all_units: List[Tuple[Point2, Point2]] = None  # For spatial partitioning
    ) -> Point2:
        """
        Calculate desired velocity using Boids algorithm.
        OPTIMIZED: Uses spatial partitioning for O(N^2) -> O(N) when all_units provided.

        Args:
            unit_position: Current position of the unit
            unit_velocity: Current velocity of the unit
            nearby_units: List of (position, velocity) tuples (optional, if not provided uses spatial partition)
            all_units: List of all (position, velocity) tuples for spatial partitioning optimization

        Returns:
            Desired velocity vector (Point2)
        """
        # OPTIMIZATION: Use spatial partitioning if available and all_units provided
        if all_units is not None and nearby_units is None:
            max_radius = max(
                self.config.separation_distance,
                self.config.cohesion_radius,
                self.config.alignment_radius or 10.0
            )
            
            # Option 1: K-D Tree (O(N log N) for sparse distributions)
            if self._use_kd_tree and self.kd_tree:
                self.kd_tree.build(all_units)
                nearby_units = self.kd_tree.query_radius(unit_position, max_radius)
            # Option 2: Grid-based (O(N) for dense distributions)
            elif self._use_spatial_partition and self.spatial_partition:
                self.spatial_partition.add_units(all_units)
                nearby_units = self.spatial_partition.query_nearby(unit_position, max_radius)
        
        # Fallback to provided nearby_units if spatial partition not available
        if nearby_units is None:
            nearby_units = []
        
        if not nearby_units:
            return unit_velocity

        # Separation: Steer away from nearby units
        separation = self._calculate_separation(unit_position, nearby_units)

        # Alignment: Steer toward average velocity of nearby units
        alignment = self._calculate_alignment(unit_velocity, nearby_units)

        # Cohesion: Steer toward average position of nearby units
        cohesion = self._calculate_cohesion(unit_position, nearby_units)

        # Combine behaviors with weights
        desired_velocity = Point2((
            unit_velocity.x
            + separation.x * self.config.separation_weight
            + alignment.x * self.config.alignment_weight
            + cohesion.x * self.config.cohesion_weight,
            unit_velocity.y
            + separation.y * self.config.separation_weight
            + alignment.y * self.config.alignment_weight
            + cohesion.y * self.config.cohesion_weight
        ))

        # Limit speed
        return _normalize(desired_velocity, self.config.max_speed)


    def _calculate_separation(
        self,
        unit_position: Point2,
        nearby_units: List[Tuple[Point2, Point2]]
    ) -> Point2:
        """Calculate separation force (steer away from neighbors)."""
        separation_force = _zero_point()
        neighbor_count = 0

        for neighbor_pos, _ in nearby_units:
            distance = _distance(unit_position, neighbor_pos)

            if 0 < distance < self.config.separation_distance:
                # Steer away from neighbor
                away_vector = Point2((
                    unit_position.x - neighbor_pos.x,
                    unit_position.y - neighbor_pos.y
                ))
                # Normalize and weight by distance (closer = stronger)
                weight = 1.0 / distance
                separation_force = Point2((
                    separation_force.x + away_vector.x * weight,
                    separation_force.y + away_vector.y * weight
                ))
                neighbor_count += 1

        if neighbor_count > 0:
            separation_force = Point2((
                separation_force.x / neighbor_count,
                separation_force.y / neighbor_count
            ))

        return separation_force


    def _calculate_alignment(
        self,
        unit_velocity: Point2,
        nearby_units: List[Tuple[Point2, Point2]]
    ) -> Point2:
        """Calculate alignment force (steer toward average neighbor velocity)."""
        neighbor_velocities = []
        for _, neighbor_vel in nearby_units:
            if _magnitude(neighbor_vel) < self.config.alignment_radius:
                neighbor_velocities.append(neighbor_vel)

        if not neighbor_velocities:
            return _zero_point()

        avg_velocity = _average_points(neighbor_velocities)
        # Steer toward average velocity
        return Point2((
            avg_velocity.x - unit_velocity.x,
            avg_velocity.y - unit_velocity.y
        ))


    def _calculate_cohesion(
        self,
        unit_position: Point2,
        nearby_units: List[Tuple[Point2, Point2]]
    ) -> Point2:
        """Calculate cohesion force (steer toward average neighbor position)."""
        neighbor_positions = [
            neighbor_pos for neighbor_pos, _ in nearby_units
            if _distance(unit_position, neighbor_pos) < self.config.cohesion_radius
        ]

        if not neighbor_positions:
            return _zero_point()

        avg_position = _average_points(neighbor_positions)
        # Steer toward average position
        return Point2((
            avg_position.x - unit_position.x,
            avg_position.y - unit_position.y
        ))


class MicroController:
    """
Micro Controller - Main interface for swarm control

This class integrates Potential Field and Boids algorithms
to provide comprehensive swarm control for drone applications.

Real-world applications:
- Drone swarm formation flying
- Autonomous vehicle platooning
- Multi-agent coordination
- Obstacle avoidance in cluttered environments
    """


    def __init__(self, bot=None, config: SwarmConfig = None, use_optimization: bool = True):
        """
        Initialize Micro Controller.

        Args:
            bot: BotAI instance (optional, for SC2 integration)
            config: Swarm configuration
            use_optimization: Enable spatial partitioning optimization (default: True)
        """
        self.bot = bot
        self.config = config or SwarmConfig()
        self.potential_field = PotentialFieldController(config)
        # OPTIMIZATION: Enable spatial partitioning by default for O(N^2) -> O(N) optimization
        # Use Grid-based for dense distributions (default), K-D Tree for sparse (< 200 units)
        # Grid-based is O(N) and works better for clustered units like Zerglings
        self.boids = BoidsController(config, use_kd_tree=False)  # Grid-based is default and faster


def calculate_swarm_movement(
    # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
    # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
    # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
    self,
    unit_position: Point2,
    target_position: Point2,
    nearby_units: List[Point2],
    obstacles: List[Point2] = None
) -> Point2:
    """
Calculate optimal movement using combined algorithms.

Args:
unit_position: Current unit position
target_position: Target/goal position
nearby_units: Positions of nearby units
obstacles: Positions of obstacles

Returns:
Optimal movement direction (Point2)
    """


 # Use Potential Field for goal-oriented movement with obstacle avoidance
potential_force = self.potential_field.calculate_potential_field(
    unit_position, target_position, nearby_units, obstacles
)

return potential_force


def calculate_flocking_behavior(
    self,
    unit_position: Point2,
    unit_velocity: Point2,
    nearby_units: List[Tuple[Point2, Point2]]
) -> Point2:
    """
Calculate natural flocking behavior using Boids algorithm.

Args:
unit_position: Current unit position
unit_velocity: Current unit velocity
nearby_units: List of (position, velocity) for nearby units

Returns:
Desired velocity for natural flocking (Point2)
    """


return self.boids.calculate_boids_velocity(
    unit_position, unit_velocity, nearby_units
)


def execute_formation_control(
    self,
    units: List[Any],  # SC2 Units or mock units
    formation_center: Point2,
        formation_type: str = "circle"
) -> Dict[Any, Point2]:
    """
Execute formation control for a group of units.

Args:
units: List of units to control
formation_center: Center point of formation
        formation_type: Type of formation ("circle", "line", "wedge")

Returns:
Dictionary mapping units to target positions
    """


unit_positions = [self._get_unit_position(u) for u in units]
target_positions = {}

if formation_type == "circle":
    pass
radius = self.config.cohesion_radius
angle_step = 2 * math.pi / len(units) if units else 0

for i, unit in enumerate(units):
    pass
angle = i * angle_step
target_pos = Point2((
    formation_center.x + radius * math.cos(angle),
    formation_center.y + radius * math.sin(angle)
))
target_positions[unit] = target_pos

elif formation_type == "line":
    pass
spacing = self.config.separation_distance
start_offset = -(len(units) - 1) * spacing / 2

for i, unit in enumerate(units):
    pass
target_pos = Point2((
    formation_center.x + start_offset + i * spacing,
    formation_center.y
))
target_positions[unit] = target_pos

elif formation_type == "wedge":
    # V-formation (common in drone swarms)
spacing = self.config.separation_distance
for i, unit in enumerate(units):
    pass
row = i // 3  # 3 units per row
col = i % 3 - 1  # -1, 0, 1
target_pos = Point2((
    formation_center.x + row * spacing * 0.5,
    formation_center.y + col * spacing
))
target_positions[unit] = target_pos

return target_positions


def _get_unit_position(self, unit: Any) -> Point2:
    """Extract position from unit (handles both SC2 and mock units)."""
    if hasattr(unit, 'position'):

        pass


pos = unit.position
if hasattr(pos, 'x') and hasattr(pos, 'y'):
    pass
return Point2((pos.x, pos.y))
return Point2((0.0, 0.0))


def execute_baneling_vs_marines(
    self,
    banelings: List[Any],
    marines: List[Any]
) -> List[Tuple[Any, Point2]]:
    """
Specialized micro for banelings vs marines.
Uses potential field to find optimal detonation positions.

Args:
banelings: List of baneling units
marines: List of marine units

Returns:
List of (baneling, target_position) tuples
    """


if not marines or not banelings:
    pass
return []

# Calculate marine cluster centers
marine_positions = [self._get_unit_position(m) for m in marines]
cluster_centers = self._find_clusters(marine_positions, radius=3.0)

# Assign banelings to clusters using potential field
assignments = []
for baneling in banelings:
    pass
baneling_pos = self._get_unit_position(baneling)

# Find closest cluster
best_cluster = None
min_distance = float('inf')
for cluster in cluster_centers:
    pass
distance = baneling_pos.distance_to(cluster)
if distance < min_distance:
    pass
min_distance = distance
best_cluster = cluster

if best_cluster:
    pass
assignments.append((baneling, best_cluster))

return assignments


def _find_clusters(
    self,
    positions: List[Point2],
    radius: float = 3.0
) -> List[Point2]:
    """
Find cluster centers using simple k-means-like approach.

Args:
positions: List of positions
radius: Cluster radius

Returns:
List of cluster center positions
    """


if not positions:
    pass
return []

clusters = []
used_positions = set()

for pos in positions:
    pass
if pos in used_positions:
    pass
continue

# Find all positions within radius
cluster_members = [p for p in positions
                   if _distance(pos, p) <= radius]

if cluster_members:
    # Calculate cluster center
clusters.append(_average_points(cluster_members))

# Mark as used
used_positions.update(cluster_members)

return clusters if clusters else [positions[0]]
