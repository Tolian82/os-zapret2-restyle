#!/bin/sh

strategy_lab_tls12_request()
{
    strategy_lab_request_python tls12 ipv4 "$1" "$2"
}

strategy_lab_tls12_bound_request()
{
    strategy_lab_request_python tls12-bound "$1" "$2" "$3"
}

strategy_lab_http_request()
{
    strategy_lab_request_python http ipv4 "$1" "$2"
}

strategy_lab_http_bound_request()
{
    strategy_lab_request_python http-bound "$1" "$2" "$3"
}
