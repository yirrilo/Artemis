package ${packageName}

//TODO: add the missing inheritance
class MergeSort /*<remove>*/ : SortStrategy /*</remove>*/{

    /***********************************************************************
     * Sort the array a using mergesort
     */
    /*<remove>*/override /*</remove>*/fun performSort(a: Array<Int>) {
        val n = a.size
        val aux = Array<Int>(n) { 0 }
        sort(a, aux, 0, n)
    }

    /***********************************************************************
     * Merge the subarrays a[lo] .. a[mid-1] and a[mid] .. a[hi-1] into
     * a[lo] .. a[hi-1] using the auxilliary array aux[] as scratch space.
     *
     * Precondition:   the two subarrays are in ascending order
     * Postcondition:  a[lo] .. a[hi-1] is in ascending order
     *
     */
    private fun merge(a: Array<Int>, aux: Array<Int>, lo: Int, mid: Int, hi: Int) {
        var i = lo
        var j = mid
        for (k in lo until hi) {
            when {
                i == mid -> aux[k] = a[j++]
                j == hi -> aux[k] = a[i++]
                a[j] < a[i] -> aux[k] = a[j++]
                else -> aux[k] = a[i++]
            }
        }

        // copy back
        for (k in lo until hi)
            a[k] = aux[k]
    }


    /***********************************************************************
     * Mergesort the subarray a[lo] .. a[hi-1], using the
     * auxilliary array aux[] as scratch space.
     */
    private fun sort(a: Array<Int>, aux: Array<Int>, lo: Int, hi: Int) {

        // base case
        if (hi - lo <= 1) return

        // sort each half, recursively
        val mid = lo + (hi - lo) / 2
        sort(a, aux, lo, mid)
        sort(a, aux, mid, hi)

        // merge back together
        merge(a, aux, lo, mid, hi)
    }

}
