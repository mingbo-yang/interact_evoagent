"use client";

type Props = {
  text: string;
};

export default function DiffViewer({ text }: Props) {
  const lines = text.split("\n");
  return (
    <div className="diff">
      {lines.map((ln, i) => {
        let cls = "ctx";
        if (ln.startsWith("+") && !ln.startsWith("+++")) cls = "add";
        else if (ln.startsWith("-") && !ln.startsWith("---")) cls = "del";
        else if (ln.startsWith("@@")) cls = "hunk";
        else if (ln.startsWith("diff ") || ln.startsWith("index ") || ln.startsWith("+++") || ln.startsWith("---"))
          cls = "hunk";
        return (
          <div key={i} className={`line ${cls}`}>
            {ln || " "}
          </div>
        );
      })}
    </div>
  );
}
