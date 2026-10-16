const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, Header, Footer, PageNumber, TableOfContents, PageBreak,
  LevelFormat, convertInchesToTwip, VerticalAlign,
} = require("docx");

const FIG = __dirname;

// ---------------------------------------------------------------------
// small helpers
// ---------------------------------------------------------------------

function h1(text, bookmarkId) {
  const { Bookmark } = require("docx");
  const children = bookmarkId
    ? [new Bookmark({ id: bookmarkId, children: [new TextRun(text)] })]
    : [new TextRun(text)];
  return new Paragraph({ children, heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 } });
}
function h3(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 } });
}

// parts: array of strings or {t, sub, sup, i, b} objects
function runs(parts) {
  return parts.map((part) => {
    if (typeof part === "string") return new TextRun(part);
    return new TextRun({
      text: part.t,
      subScript: !!part.sub,
      superScript: !!part.sup,
      italics: !!part.i,
      bold: !!part.b,
    });
  });
}

function p(parts, opts = {}) {
  return new Paragraph({ children: runs(Array.isArray(parts) ? parts : [parts]), spacing: { after: 160 }, ...opts });
}

function eq(parts, label) {
  const children = runs(parts);
  if (label) children.push(new TextRun({ text: "    (" + label + ")", italics: true, size: 20 }));
  return new Paragraph({
    children,
    alignment: AlignmentType.CENTER,
    spacing: { before: 160, after: 160 },
  });
}

function bullets(items) {
  return items.map((item) => new Paragraph({
    children: runs(Array.isArray(item) ? item : [item]),
    numbering: { reference: "bullet-list", level: 0 },
    spacing: { after: 80 },
  }));
}

function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 20 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 280 },
  });
}

const FIGURE_DIMENSIONS = {
  "demo_closed_loop.png": [1260, 1120],
  "experiment_01_temperature_calibration.png": [840, 700],
  "experiment_02_level_calibration.png": [840, 700],
  "experiment_03_flow_calibration.png": [840, 700],
  "experiment_04_open_loop_temperature_response.png": [1120, 630],
  "experiment_05_closed_loop_temperature_control.png": [1120, 840],
  "experiment_07_temperature_disturbance_rejection.png": [1120, 630],
  "experiment_08_closed_loop_level_control.png": [1120, 840],
  "experiment_09_level_disturbance_rejection.png": [1120, 630],
  "experiment_10_coupled_full_system.png": [1120, 1120],
  "experiment_11_p_pi_pid_comparison.png": [1120, 700],
};

function figure(fileName, widthPx, name) {
  const filePath = path.join(FIG, fileName);
  const data = fs.readFileSync(filePath);
  const [origW, origH] = FIGURE_DIMENSIONS[fileName];
  const w = widthPx;
  const h = Math.round(widthPx * (origH / origW));
  return [
    new Paragraph({
      children: [new ImageRun({ data, type: "png", transformation: { width: w, height: h } })],
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: 40 },
    }),
    caption(name),
  ];
}

function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.header ? { type: ShadingType.CLEAR, fill: "E8E8E8" } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({ text: String(text), bold: !!opts.header, size: opts.size || 20 })],
      alignment: opts.align || AlignmentType.LEFT,
    })],
  });
}

function table(headerRow, rows, colWidths) {
  const total = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({
        tableHeader: true,
        cantSplit: true,
        children: headerRow.map((t, i) => cell(t, { header: true, width: colWidths[i], align: AlignmentType.CENTER })),
      }),
      ...rows.map((r) => new TableRow({
        cantSplit: true,
        children: r.map((t, i) => cell(t, { width: colWidths[i], align: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER })),
      })),
    ],
  });
}

function hr() {
  return new Paragraph({
    text: "",
    border: { bottom: { color: "999999", space: 1, style: BorderStyle.SINGLE, size: 6 } },
    spacing: { after: 200 },
  });
}

module.exports = { h1, h2, h3, p, eq, bullets, figure, table, hr, runs, caption,
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Header, Footer, PageNumber, TableOfContents, PageBreak, LevelFormat,
  convertInchesToTwip };
