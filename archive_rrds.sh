[ -z "$RRD_DIR" ] && RRD_DIR=/var/www/cmdb/rrd-files
[ -z "$RRD_ACCOUNTING_DIR" ] && RRD_ACCOUNTING_DIR="$RRD_DIR/accounting"
[ -z "$CSV_DIR" ] && CSV_DIR=/var/www/cmdb/csv-files
[ -z "$CSV_ACCOUNTING_DIR" ] && CSV_ACCOUNTING_DIR="$CSV_DIR/accounting"

[ -d "$CSV_DIR" ] || mkdir -p "$CSV_DIR"
[ -d "$CSV_ACCOUNTING_DIR" ] || mkdir -p "$CSV_ACCOUNTING_DIR"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rrd2csv="$script_dir/rrd2csv.py"

for rrd in $RRD_DIR/*.rrd; do
    f="$(basename "$rrd")"
    csv="$CSV_DIR/${f%rrd}csv"
    "$rrd2csv" "$rrd" "$csv"
done

for rrd in $RRD_ACCOUNTING_DIR/*.rrd; do
    f="$(basename "$rrd")"
    csv="$CSV_ACCOUNTING_DIR/${f%rrd}csv"
    "$rrd2csv" "$rrd" "$csv"
done
