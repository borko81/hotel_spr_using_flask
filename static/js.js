// Калкулира тотала в таблиците
var tds = document.getElementById('prihodi_po_grupi').getElementsByTagName('td')
var tr = document.getElementById('prihodi_po_grupi').getElementsByTagName('tr')
var sum2 = 0
for (var i = 0; i < tds.length; i++) {
  if (tds[i].className == 'count-me2') {
    sum2 += isNaN(tds[i].innerHTML) ? 0 : parseInt(tds[i].innerHTML)
  }
}
document.getElementById('prihodi_po_grupi').innerHTML +=
            '<table class="result"><tr><td>Всичко</td><td></td><td>' + sum2 + '</td></tr></table>'

// Търсачката

function myFunction () {

  var input, filter, table, td, i, txtValue
  let tr
  input = document.getElementById('myInput')
  filter = input.value.toUpperCase()
  table = document.getElementById('prihodi_po_grupi')
  tr = table.getElementsByTagName('tr')

  for (i = 1; i < tr.length - 1; i++) {
    tds = tr[i].getElementsByTagName('td')
    var matches = false

    for (j = 0; j < tds.length; j++) {
	  if (tds[j]) {
	    txtValue = tds[j].textContent || tds[j].innerText
	    if (txtValue.toUpperCase().indexOf(filter) > -1) {
	      matches = true
	    }
	  }
    }

    if (matches == true) {
	  tr[i].style.display = ''
    } else {
	  tr[i].style.display = 'none'
    }
  }
}

// Същата с ново име щото не ми се занимава да махам тотал в отделна функция///

function myFunction2 () {

  var input, filter, table, td, i, txtValue
  let tr
  input = document.getElementById('myInput2')
  filter = input.value.toUpperCase()
  table = document.getElementById('prihodi_po_grupi2')
  tr = table.getElementsByTagName('tr')

  for (i = 1; i < tr.length - 1; i++) {
    tds = tr[i].getElementsByTagName('td')
    var matches = false

    for (j = 0; j < tds.length; j++) {
    if (tds[j]) {
      txtValue = tds[j].textContent || tds[j].innerText
      if (txtValue.toUpperCase().indexOf(filter) > -1) {
        matches = true
      }
    }
    }

    if (matches == true) {
    tr[i].style.display = ''
    } else {
    tr[i].style.display = 'none'
    }
  }
}
