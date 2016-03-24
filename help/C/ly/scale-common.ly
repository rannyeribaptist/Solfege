
\paper{
  indent=0\mm
  oddFooterMarkup=##f
  oddHeaderMarkup=##f
  bookTitleMarkup = ##f
  scoreTitleMarkup = ##f
}

\layout { 
    ragged-right = ##t
    \context {
      \Staff
      \remove "Time_signature_engraver"
    }
}

