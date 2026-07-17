import { markdown } from "@codemirror/lang-markdown";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { basicSetup } from "codemirror";
import { useEffect, useRef } from "react";

type CodeMirrorEditorProps = { value: string; onChange: (value: string) => void; onSave: () => void };

export function CodeMirrorEditor({ value, onChange, onSave }: CodeMirrorEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const changeRef = useRef(onChange);
  const saveRef = useRef(onSave);
  changeRef.current = onChange;
  saveRef.current = onSave;

  useEffect(() => {
    if (!containerRef.current) return;
    const view = new EditorView({
      parent: containerRef.current,
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          markdown(),
          keymap.of([{ key: "Mod-s", preventDefault: true, run: () => { saveRef.current(); return true; } }]),
          EditorView.lineWrapping,
          EditorView.updateListener.of((update) => {
            if (update.docChanged) changeRef.current(update.state.doc.toString());
          }),
          EditorView.theme({
            "&": { height: "100%", backgroundColor: "#fffefa", fontSize: "14px" },
            ".cm-content": { padding: "24px", fontFamily: '"Azeret Mono", ui-monospace, monospace', lineHeight: "1.7" },
            ".cm-gutters": { backgroundColor: "#f4f2ed", color: "#8b918b", borderRight: "1px solid #deddd6" },
            ".cm-activeLine, .cm-activeLineGutter": { backgroundColor: "#edf5f1" },
            ".cm-focused": { outline: "none" },
          }),
        ],
      }),
    });
    viewRef.current = view;
    return () => { view.destroy(); viewRef.current = null; };
  }, []);

  useEffect(() => {
    const view = viewRef.current;
    if (!view || view.state.doc.toString() === value) return;
    view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } });
  }, [value]);

  return <div ref={containerRef} style={{ height: "100%", minHeight: 0 }} />;
}
