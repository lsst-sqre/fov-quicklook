import { useEffect, useRef } from 'react';

/**
 * 値の変更時のみコールバックを実行するカスタムフック
 * 初回レンダリング時は実行されない
 * @param value 監視する値
 * @param callback 値が変更された時に実行するコールバック
 */
export function useOnChange<T>(value: T, callback: (newValue: T, oldValue: T | undefined) => void): void {
  const isFirstRender = useRef(true);
  const prevValue = useRef<T | undefined>(undefined);

  useEffect(() => {
    // 初回レンダリング時はコールバックを実行せず、値を記録するだけ
    if (isFirstRender.current) {
      isFirstRender.current = false;
      prevValue.current = value;
      return;
    }

    // 値が変わった場合のみコールバックを実行
    if (value !== prevValue.current) {
      callback(value, prevValue.current);
      prevValue.current = value;
    }
  }, [value, callback]);
}
