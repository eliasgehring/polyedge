import os

from .domain import BacktestResult

from .config import (
    STARTING_CASH,
    THRESHOLD,
    MAX_POSITION_SIZE,
    EDGE_SIZE_MULTIPLIER,
    VERBOSE,
    RESULT_STATUS,
)

from .paths import (
    PROJECT_ROOT,
    HISTORICAL_DATA_FILE,
    RESULT_LOGS_DIR,
    RUN_METADATA_FILE,
)
from .data_loading import load_historical_data
from .portfolio import create_portfolio, apply_fill, compute_portfolio_value
from .signals import generate_signal
from .risk import get_trade_decision
from .execution import simulate_fill
from .console_report import print_header, report_state, report_summary
from .run_log import initialize_csv_log, log_step_to_csv
from .settlement import check_exit_conditions
from .experiment_tracking import log_run_metadata,file_sha256
from .sizing import compute_trade_size
from .portfolio_validation import validate_portfolio_state
from .data_validation import load_rows, build_diagnostics


def get_next_run_filepath() -> str:
    os.makedirs(RESULT_LOGS_DIR, exist_ok=True)

    existing_files = os.listdir(RESULT_LOGS_DIR)
    run_numbers = []

    for filename in existing_files:
        if filename.startswith("run_") and filename.endswith(".csv"):
            try:
                number = int(filename.split("_")[1].split(".")[0])
                run_numbers.append(number)
            except ValueError:
                pass

    next_run_number = max(run_numbers, default=0) + 1
    return os.path.join(RESULT_LOGS_DIR, f"run_{next_run_number}.csv")


def print_data_load_summary(historical_filepath: str, historical_data) -> None:
    print("\n" + "=" * 60)
    print("DATA LOAD")
    print("=" * 60)
    print(f"Historical file: {historical_filepath}")
    print(f"Rows loaded: {len(historical_data)}")

    if historical_data:
        first_timestamp, first_market, first_bookmaker_prob, first_row_type = historical_data[0]
        print("First row preview:")
        print(f"  timestamp       : {first_timestamp}")
        print(f"  market_id       : {first_market.market_id}")
        print(f"  row_type        : {first_row_type}")
        print(f"  best_bid        : {first_market.best_bid:.6f}")
        print(f"  best_ask        : {first_market.best_ask:.6f}")
        print(f"  bookmaker_prob  : {first_bookmaker_prob:.6f}")

    print("=" * 60)


def run_simulation(
    threshold=None,
    edge_size_multiplier=None,
    historical_filepath=None,
):
    portfolio = create_portfolio(STARTING_CASH)

    threshold_value = threshold if threshold is not None else THRESHOLD
    edge_multiplier_value = (
        edge_size_multiplier
        if edge_size_multiplier is not None
        else EDGE_SIZE_MULTIPLIER
    )
    
    log_filepath = get_next_run_filepath()
    initialize_csv_log(log_filepath)
    if historical_filepath is None:
        historical_filepath = HISTORICAL_DATA_FILE

    diagnostic_rows = load_rows(historical_filepath)
    diagnostics = build_diagnostics(diagnostic_rows)
    
    if diagnostics["hard_fail"]:
        raise ValueError(
        "Refusing to run backtest because dataset diagnostics failed."
    )

    historical_data = load_historical_data(historical_filepath)
    print_data_load_summary(historical_filepath, historical_data)

    total_trades = 0
    buy_yes_count = 0
    buy_no_count = 0
    hold_count = 0
    risk_rejection_count = 0

    peak_value = STARTING_CASH
    max_drawdown = 0.0
    last_market = None
    latest_market_state_by_id = {}

    for i, (timestamp, market, bookmaker_prob, row_type) in enumerate(historical_data):
        last_market = market
        latest_market_state_by_id[market.market_id] = market

        if VERBOSE:
            print_header(f"Step {i + 1} | Time {timestamp}")
            print(f"MARKET ID: {market.market_id}")
            
            
        prev_value = compute_portfolio_value(portfolio, latest_market_state_by_id)
        fill = None
        signal = None
        approved = False
        reason = "no decision yet"

        exit_triggered = False
        exit_reason = ""
        exit_side = ""
        realized_pnl = 0.0

        exit_triggered, exit_reason, exit_side, realized_pnl = check_exit_conditions(
            portfolio,
            market,
        )

        if exit_triggered:
            if VERBOSE:
                print(f"EXIT TRIGGERED: {exit_reason}")

            approved = False
            reason = exit_reason
            validate_portfolio_state(portfolio)

        else:
            signal = generate_signal(
                market=market,
                bookmaker_prob=bookmaker_prob,
                threshold=threshold_value,
            )

            approved, reason = get_trade_decision(
                signal,
                portfolio,
                MAX_POSITION_SIZE,
            )

            if VERBOSE:
                print(
                    f"SIGNAL: {signal.action} | "
                    f"APPROVED: {approved} | "
                    f"REASON: {reason}"
                )

            if signal.action == "HOLD":
                hold_count += 1
            elif not approved:
                risk_rejection_count += 1

            if approved:
                dynamic_size = compute_trade_size(
                    signal=signal,
                    max_position_size=MAX_POSITION_SIZE,
                    edge_size_multiplier=edge_multiplier_value,
                )

                if VERBOSE:
                    print(f"DYNAMIC SIZE: {dynamic_size:.3f}")

                if dynamic_size > 0:
                    fill = simulate_fill(signal, market, dynamic_size)

                    if fill is not None:
                        apply_fill(portfolio, fill, market)
                        validate_portfolio_state(portfolio)

                        total_trades += 1

                        if fill.side == "BUY_YES":
                            buy_yes_count += 1
                        elif fill.side == "BUY_NO":
                            buy_no_count += 1
                else:
                    if VERBOSE:
                        print("DYNAMIC SIZE <= 0, no fill")
            else:
                if VERBOSE:
                    print("TRADE NOT APPROVED")
                    
                    
        current_value = compute_portfolio_value(portfolio, latest_market_state_by_id)        
        step_pnl = current_value - prev_value

        if current_value > peak_value:
            peak_value = current_value

        drawdown = peak_value - current_value
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        validate_portfolio_state(portfolio)

        if VERBOSE:
            report_state(
                signal=signal,
                approved=approved,
                reason=reason,
                fill=fill,
                portfolio=portfolio,
                market=market,
                latest_market_state_by_id=latest_market_state_by_id,
                exit_triggered=exit_triggered,
                exit_reason=exit_reason,
                exit_side=exit_side,
                realized_pnl=realized_pnl,
                step_pnl=step_pnl,
            )

        log_step_to_csv(
            log_filepath,
            i + 1,
            timestamp,
            row_type,
            signal,
            approved,
            reason,
            fill,
            portfolio,
            market,
            latest_market_state_by_id,
            exit_triggered,
            exit_reason,
            exit_side,
            realized_pnl,
        )

    final_value = compute_portfolio_value(portfolio, latest_market_state_by_id)

    report_summary(
        total_trades,
        buy_yes_count,
        buy_no_count,
        hold_count,
        risk_rejection_count,
        peak_value,
        max_drawdown,
        final_value,)
    
    
    log_run_metadata(
        RUN_METADATA_FILE,
    {
        "run_file": os.path.basename(log_filepath),
        "result_status": RESULT_STATUS,
        "threshold": threshold_value,
        "edge_size_multiplier": edge_multiplier_value,
        "max_position_size": MAX_POSITION_SIZE,
        "dataset_hash": file_sha256(historical_filepath),
        "dataset_rows": diagnostics["rows"],
        "dataset_markets": diagnostics["markets"],
        "dataset_pregame_rows": diagnostics["pregame_rows"],
        "dataset_settlement_rows": diagnostics["settlement_rows"],
        "dataset_hard_fail": diagnostics["hard_fail"],
    },
)
    print(f"\nRun log saved to: {log_filepath}")

    return BacktestResult(
        result_status=RESULT_STATUS,
        dataset_path=str(historical_filepath),
        total_trades=total_trades,
        buy_yes_count=buy_yes_count,
        buy_no_count=buy_no_count,
        hold_count=hold_count,
        risk_rejection_count=risk_rejection_count,
        start_value=STARTING_CASH,
        final_value=final_value,
        total_return=final_value - STARTING_CASH,
        peak_value=peak_value,
        max_drawdown=max_drawdown,
    )

if __name__ == "__main__":
    run_simulation()