#set document(
  title: "Assignment 1: Process Oriented Architecure - Project Documentation",
)

#set page(
paper: "a4",
numbering: "1/1")

#set text(
font: "Nimbus Sans",
size: 12pt
)

#show link: underline

#title()

#align(center)[
  Group 1, Team Members: \
  Michael Schütz, Gianluca Ielpo, Eva Amromin
]

#outline()
#pagebreak()

#include "overview.typ"
#include "architecture.typ"
#include "process.typ"
#include "services.typ"


= Contributions

#table(
  columns: (30%, 70%),
  table.header([*Person*], [*Tasks*]),
  [Michael], [Order Service, Documentation],
  [Eva], [Inventory Service, Dashboard Service, Documentation],
  [Gianluca], [Factory Service (including hardware), Documentation],
)