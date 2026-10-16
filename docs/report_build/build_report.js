const fs = require("fs");
const path = require("path");
const { InternalHyperlink } = require("docx");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType,
  Header, Footer, PageNumber, PageBreak,
  LevelFormat, convertInchesToTwip,
} = require("./helpers.js");

const part1 = require("./content_part1.js");
const part2 = require("./content_part2.js");

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

const TOC_ENTRIES = [
  ["1. Introduction", "sec1"],
  ["2. Problem Definition and Objectives", "sec2"],
  ["3. System Architecture", "sec3"],
  ["4. Mathematical Model of the Virtual Plant", "sec4"],
  ["5. Instrumentation", "sec5"],
  ["6. Control Architecture", "sec6"],
  ["7. Disturbances and Fault Injection", "sec7"],
  ["8. Simulation Methodology", "sec8"],
  ["9. Experiments and Results", "sec9"],
  ["10. Performance Analysis", "sec10"],
  ["11. Validation and Testing", "sec11"],
  ["12. Limitations", "sec12"],
  ["13. Industrial Relevance", "sec13"],
  ["14. Future Improvements", "sec14"],
  ["15. Conclusion", "sec15"],
  ["Appendix A: Engineering Assumptions", "secA"],
  ["Appendix B: Reproducing These Results", "secB"],
];

const tocHeading = new Paragraph({ text: "Table of Contents", heading: "Heading1", spacing: { after: 240 } });
const tocEntries = TOC_ENTRIES.map(([title, id]) => new Paragraph({
  children: [new InternalHyperlink({
    anchor: id,
    children: [new TextRun({ text: title, style: "Hyperlink" })],
  })],
  spacing: { after: 140 },
}));
const toc = [tocHeading, ...tocEntries];

const emptyFooter = new Footer({ children: [new Paragraph("")] });
const pageNumberFooter = new Footer({
  children: [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT] })],
    }),
  ],
});

const body = [
  ...part1.titlePage,
  pageBreak(),
  ...toc,
  pageBreak(),
  ...part1.introduction,
  ...part1.objectives,
  ...part1.architecture,
  ...part1.mathModel,
  ...part1.instrumentation,
  ...part1.controlArchitecture,
  ...part2.disturbancesAndFaults,
  ...part2.methodology,
  ...part2.experiments,
  ...part2.performanceAnalysis,
  ...part2.validation,
  ...part2.limitations,
  ...part2.industrialRelevance,
  ...part2.futureImprovements,
  ...part2.conclusion,
  pageBreak(),
  ...part2.appendixA,
  ...part2.appendixB,
];

const doc = new Document({
  features: { updateFields: true },
  numbering: {
    config: [
      {
        reference: "bullet-list",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.18) } } } },
        ],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 22 } },
      heading1: { run: { size: 30, bold: true, color: "1F3864" }, paragraph: { spacing: { before: 360, after: 160 } } },
      heading2: { run: { size: 25, bold: true, color: "2E5395" }, paragraph: { spacing: { before: 260, after: 120 } } },
      heading3: { run: { size: 23, bold: true, italics: true, color: "2E5395" }, paragraph: { spacing: { before: 200, after: 100 } } },
    },
  },
  sections: [
    {
      properties: {
        titlePage: true,
        page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } },
      },
      footers: { first: emptyFooter, default: pageNumberFooter },
      children: body,
    },
  ],
});

const outPath = path.join(__dirname, "..", "Aqualoop_Technical_Report.docx");

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log("wrote", outPath, buffer.length, "bytes");
});
