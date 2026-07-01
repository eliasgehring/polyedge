from backtest import run_simulation


THRESHOLDS = [
    0.01,
    0.02,
    0.03,
    0.05,
    0.07,
    0.10,
]

EDGE_SIZE_MULTIPLIERS = [
    100,
    200,
    500,
]


def main():
    total_runs = len(THRESHOLDS) * len(EDGE_SIZE_MULTIPLIERS)
    run_number = 0

    print("\n" + "=" * 60)
    print("RUNNING STRATEGY GRID")
    print("=" * 60)
    print(f"Total runs: {total_runs}")

    for threshold in THRESHOLDS:
        for edge_size_multiplier in EDGE_SIZE_MULTIPLIERS:
            run_number += 1

            print("\n" + "-" * 60)
            print(f"Run {run_number}/{total_runs}")
            print(f"threshold            : {threshold}")
            print(f"edge_size_multiplier : {edge_size_multiplier}")
            print("-" * 60)

            run_simulation(
                threshold=threshold,
                edge_size_multiplier=edge_size_multiplier,
            )

    print("\n" + "=" * 60)
    print("GRID COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()