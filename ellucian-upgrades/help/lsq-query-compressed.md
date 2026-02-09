lsq-query: Run Datalog query against Logseq

USAGE: just lsq-query "QUERY" PREREQ: Logseq HTTP API enabled

SYNTAX: \[:find ?var :where [?b :attr ?val]\] ATTRS: :block/content, :block/uuid, :block/page, :block/marker,
:block/name

EX: just lsq-query "\[:find (pull ?b [\*]) :where [?b :block/marker "TODO"]\]"

RELATED: lsq-blocks (page blocks), lsq-find (search), lsq-recent
