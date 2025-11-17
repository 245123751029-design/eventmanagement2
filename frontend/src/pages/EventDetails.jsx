import React, { useEffect, useState, useContext } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from '@/App';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Calendar, MapPin, Users, User, ArrowLeft, Ticket } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EventDetails = () => {
  const { id } = useParams();
  const { user, login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [ticketTypes, setTicketTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showBookingDialog, setShowBookingDialog] = useState(false);
  const [selectedTicketType, setSelectedTicketType] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    fetchEvent();
    fetchTicketTypes();
  }, [id]);

  const fetchEvent = async () => {
    try {
      const response = await axios.get(`${API}/events/${id}`);
      setEvent(response.data);
    } catch (error) {
      console.error('Error fetching event:', error);
      toast.error('Event not found');
      navigate('/events');
    } finally {
      setLoading(false);
    }
  };

  const fetchTicketTypes = async () => {
    try {
      const response = await axios.get(`${API}/events/${id}/ticket-types`);
      setTicketTypes(response.data);
    } catch (error) {
      console.error('Error fetching ticket types:', error);
    }
  };

  const handleBooking = async () => {
    if (!user) {
      toast.error('Please login to book tickets');
      login();
      return;
    }

    if (!selectedTicketType) {
      toast.error('Please select a ticket type');
      return;
    }

    if (quantity < 1) {
      toast.error('Quantity must be at least 1');
      return;
    }

    try {
      setBooking(true);
      const response = await axios.post(
        `${API}/bookings`,
        {
          event_id: id,
          ticket_type_id: selectedTicketType,
          quantity: parseInt(quantity)
        },
        { withCredentials: true }
      );

      const { booking: newBooking, requires_payment } = response.data;

      if (requires_payment) {
        // Redirect to payment
        const checkoutResponse = await axios.post(
          `${API}/bookings/checkout`,
          {
            booking_id: newBooking.id,
            origin_url: window.location.origin
          },
          { withCredentials: true }
        );
        window.location.href = checkoutResponse.data.url;
      } else {
        // Free ticket - booking confirmed
        toast.success('Booking confirmed!');
        setShowBookingDialog(false);
        navigate('/my-bookings');
      }
    } catch (error) {
      console.error('Booking error:', error);
      toast.error(error.response?.data?.detail || 'Booking failed');
    } finally {
      setBooking(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'long',
      month: 'long', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getAvailableTickets = (ticketType) => {
    return ticketType.quantity_available - ticketType.quantity_sold;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!event) return null;

  const selectedTicket = ticketTypes.find(t => t.id === selectedTicketType);
  const totalPrice = selectedTicket ? selectedTicket.price * quantity : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 py-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <Button
          data-testid="back-to-events-btn"
          onClick={() => navigate('/events')}
          variant="ghost"
          className="mb-6 hover:bg-gray-100 rounded-full"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Events
        </Button>

        <div className="bg-white rounded-3xl shadow-xl overflow-hidden border border-gray-100">
          <div className="h-80 bg-gradient-to-br from-blue-400 to-purple-500 relative">
            {event.image_url ? (
              <img src={event.image_url} alt={event.title} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Calendar className="w-24 h-24 text-white opacity-50" />
              </div>
            )}
            <div className="absolute top-6 right-6 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full font-semibold text-gray-700">
              {event.category}
            </div>
          </div>

          <div className="p-8">
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 mb-4">{event.title}</h1>
            
            <div className="flex items-center space-x-2 text-gray-600 mb-6">
              <User className="w-5 h-5" />
              <span>Organized by <span className="font-semibold">{event.creator_name}</span></span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="flex items-start space-x-3 p-4 bg-blue-50 rounded-xl">
                <Calendar className="w-6 h-6 text-blue-600 mt-1" />
                <div>
                  <p className="text-sm text-gray-600 mb-1">Date & Time</p>
                  <p className="font-semibold text-gray-900">{formatDate(event.date)}</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-purple-50 rounded-xl">
                <MapPin className="w-6 h-6 text-purple-600 mt-1" />
                <div>
                  <p className="text-sm text-gray-600 mb-1">Location</p>
                  <p className="font-semibold text-gray-900">{event.location}</p>
                </div>
              </div>
              <div className="flex items-start space-x-3 p-4 bg-green-50 rounded-xl">
                <Users className="w-6 h-6 text-green-600 mt-1" />
                <div>
                  <p className="text-sm text-gray-600 mb-1">Capacity</p>
                  <p className="font-semibold text-gray-900">{event.capacity} attendees</p>
                </div>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-3">About This Event</h2>
              <p className="text-base text-gray-700 leading-relaxed">{event.description}</p>
            </div>

            {ticketTypes.length > 0 && (
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">Tickets</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {ticketTypes.map((ticket) => {
                    const available = getAvailableTickets(ticket);
                    return (
                      <div
                        key={ticket.id}
                        data-testid={`ticket-type-${ticket.id}`}
                        className="p-5 border-2 border-gray-200 rounded-xl hover:border-blue-400 hover:shadow-md"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <h3 className="font-bold text-lg text-gray-900">{ticket.name}</h3>
                          <span className="text-xl font-bold text-blue-600">
                            {ticket.price === 0 ? 'FREE' : `$${ticket.price.toFixed(2)}`}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">
                          {available > 0 ? `${available} tickets available` : 'Sold out'}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <Button
              data-testid="book-tickets-btn"
              onClick={() => {
                if (!user) {
                  login();
                } else {
                  setShowBookingDialog(true);
                }
              }}
              disabled={ticketTypes.length === 0 || ticketTypes.every(t => getAvailableTickets(t) === 0)}
              className="w-full py-6 text-lg bg-blue-600 hover:bg-blue-700 text-white rounded-full font-semibold"
            >
              <Ticket className="w-5 h-5 mr-2" />
              {user ? 'Book Tickets' : 'Sign In to Book'}
            </Button>
          </div>
        </div>
      </div>

      {/* Booking Dialog */}
      <Dialog open={showBookingDialog} onOpenChange={setShowBookingDialog}>
        <DialogContent data-testid="booking-dialog" className="max-w-md">
          <DialogHeader>
            <DialogTitle>Book Tickets</DialogTitle>
            <DialogDescription>Select ticket type and quantity</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <label className="block text-sm font-medium mb-2">Ticket Type</label>
              <Select value={selectedTicketType || undefined} onValueChange={setSelectedTicketType}>
                <SelectTrigger data-testid="ticket-type-select">
                  <SelectValue placeholder="Select ticket type" />
                </SelectTrigger>
                <SelectContent>
                  {ticketTypes
                    .filter(t => getAvailableTickets(t) > 0)
                    .map((ticket) => (
                      <SelectItem key={ticket.id} value={ticket.id}>
                        {ticket.name} - {ticket.price === 0 ? 'FREE' : `$${ticket.price.toFixed(2)}`}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Quantity</label>
              <Input
                data-testid="quantity-input"
                type="number"
                min="1"
                max={selectedTicket ? getAvailableTickets(selectedTicket) : 1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
            {selectedTicket && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex justify-between text-sm mb-1">
                  <span>Ticket Price:</span>
                  <span className="font-semibold">${selectedTicket.price.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Quantity:</span>
                  <span className="font-semibold">{quantity}</span>
                </div>
                <div className="border-t border-gray-300 pt-2 mt-2">
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total:</span>
                    <span className="text-blue-600">${totalPrice.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}
            <Button
              data-testid="confirm-booking-btn"
              onClick={handleBooking}
              disabled={booking || !selectedTicketType}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white"
            >
              {booking ? 'Processing...' : totalPrice === 0 ? 'Confirm Booking' : 'Proceed to Payment'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EventDetails;
