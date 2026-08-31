#set document(
  title: "QuakeGuard - Technical Specification", 
  author: ("GiZano", "riccardo0731")
)

#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 3cm),
  header: context {
    // Utilizza la nuova sintassi context nativa di Typst
    if counter(page).get().first() > 1 {
      align(right)[_QuakeGuard v1.3.0 - Technical Architecture_]
    }
  },
  numbering: "1",
)

// Impostazioni tipografiche
#set text(font: "Liberation Serif", size: 11pt, lang: "en")
#set heading(numbering: "1.1.")
#set par(justify: true, leading: 0.65em)

// --- FRONTESPIZIO ---
#align(center)[
  #v(3cm)
  #text(size: 32pt, weight: "bold")[QuakeGuard]\
  #v(0.5cm)
  #text(size: 16pt)[Distributed Earthquake Early Warning System]\
  #v(0.2cm)
  #text(size: 14pt)[Technical Architecture & Protocol Specification]\
  #v(2cm)
  #text(size: 12pt)[Release: *v1.3.0* (GNSS NTP Discipline & SIL Validation)]\
  #v(0.5cm)
  #text(size: 12pt)[Core Maintainers: \@GiZano, \@riccardo0731]\
  #v(3cm)
]

#pagebreak()

// --- INDICE ---
#outline(
  title: "Table of Contents",
  depth: 3,
  indent: auto
)

#pagebreak()

// --- CAPITOLI ---
#include "01-architecture.typ"
#include "02-hardware.typ"
#include "03-security.typ"
#include "04-broker.typ"
#include "05-backend.typ"
#include "06-mobile.typ"
#include "07-deployment.typ"
#include "08-ai.typ"