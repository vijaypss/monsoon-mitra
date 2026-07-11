import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props { children: ReactNode }
interface State { error: Error | null }

/** Catches render/effect errors so the app never shows a blank white screen. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surfaced in the browser console for debugging deployed builds.
    console.error("MonsoonMitra crashed:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="mx-auto mt-16 max-w-lg rounded-2xl border border-red-200 bg-white p-6 text-center shadow-sm">
          <div className="text-3xl">🌧️</div>
          <h1 className="mt-2 text-lg font-semibold text-slate-900">Something went wrong</h1>
          <p className="mt-2 text-sm text-slate-600">
            The app hit an unexpected error and could not continue. Your data is safe.
          </p>
          <pre className="mt-3 overflow-auto rounded-lg bg-slate-50 p-3 text-left text-xs text-red-700">
            {this.state.error.message}
          </pre>
          <button
            onClick={() => { this.setState({ error: null }); location.reload(); }}
            className="mt-4 rounded-xl bg-monsoon-600 px-5 py-2 text-sm font-medium text-white hover:bg-monsoon-700"
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
