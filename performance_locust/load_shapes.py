from locust import LoadTestShape

class LowLoadShape(LoadTestShape):
    """
    Low-load scenario for general banking tests.
    Suitable for:
    - Baseline performance tests
    - Normal business hours
    - System validation
    """
    stages = [
        # Warm-up phase
        {"duration": 60, "users": 5, "spawn_rate": 1},
        # Stable low load
        {"duration": 180, "users": 10, "spawn_rate": 2},
        # Slight increase
        {"duration": 300, "users": 20, "spawn_rate": 2},
        # Gradual reduction
        {"duration": 360, "users": 5, "spawn_rate": 1},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None

class MediumLoadShape(LoadTestShape):
    """
    Medium-load scenario for general banking tests.
    Suitable for:
    - Business hours
    - Regular load tests
    - Performance validation
    """
    stages = [
        # Fast ramp-up
        {"duration": 60, "users": 20, "spawn_rate": 2},
        # Medium load phase
        {"duration": 180, "users": 35, "spawn_rate": 3},
        # Peak phase
        {"duration": 300, "users": 50, "spawn_rate": 4},
        # Controlled reduction
        {"duration": 360, "users": 20, "spawn_rate": 2},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None

class HighLoadShape(LoadTestShape):
    """
    High-load scenario for general banking tests.
    Suitable for:
    - Peak hours
    - Stress tests
    - Capacity tests
    """
    stages = [
        # Fast load buildup
        {"duration": 60, "users": 30, "spawn_rate": 5},
        # Initial peak load
        {"duration": 180, "users": 70, "spawn_rate": 5},
        # Maximum load
        {"duration": 300, "users": 100, "spawn_rate": 8},
        # Rapid load reduction
        {"duration": 360, "users": 30, "spawn_rate": 5},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None