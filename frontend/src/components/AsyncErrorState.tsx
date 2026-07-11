type AsyncErrorStateProps = {
  onRetry: () => void;
  message?: string;
};

export function AsyncErrorState({
  onRetry,
  message = "読み込みに失敗しました。"
}: AsyncErrorStateProps) {
  return (
    <div className="async-error-state" role="alert">
      <p className="error-text">{message}</p>
      <button className="icon-text-button" type="button" onClick={onRetry}>
        もう一度試す
      </button>
    </div>
  );
}
