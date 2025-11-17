import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Plus, Trash2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CreateEvent = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    date: '',
    location: '',
    capacity: '',
    category: '',
    image_url: ''
  });
  const [ticketTypes, setTicketTypes] = useState([]);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleCategoryChange = (value) => {
    setFormData({ ...formData, category: value });
  };

  const addTicketType = () => {
    setTicketTypes([...ticketTypes, { name: '', price: '', quantity_available: '' }]);
  };

  const removeTicketType = (index) => {
    setTicketTypes(ticketTypes.filter((_, i) => i !== index));
  };

  const updateTicketType = (index, field, value) => {
    const updated = [...ticketTypes];
    updated[index][field] = value;
    setTicketTypes(updated);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title || !formData.description || !formData.date || !formData.location || !formData.capacity || !formData.category) {
      toast.error('Please fill in all required fields');
      return;
    }

    if (ticketTypes.length === 0) {
      toast.error('Please add at least one ticket type');
      return;
    }

    for (const ticket of ticketTypes) {
      if (!ticket.name || ticket.price === '' || !ticket.quantity_available) {
        toast.error('Please complete all ticket type fields');
        return;
      }
    }

    try {
      setLoading(true);
      
      // Create event
      const eventResponse = await axios.post(
        `${API}/events`,
        {
          ...formData,
          capacity: parseInt(formData.capacity)
        },
        { withCredentials: true }
      );

      const eventId = eventResponse.data.id;

      // Create ticket types
      for (const ticket of ticketTypes) {
        await axios.post(
          `${API}/events/${eventId}/ticket-types`,
          {
            name: ticket.name,
            price: parseFloat(ticket.price),
            quantity_available: parseInt(ticket.quantity_available)
          },
          { withCredentials: true }
        );
      }

      toast.success('Event created successfully!');
      navigate('/my-events');
    } catch (error) {
      console.error('Error creating event:', error);
      toast.error(error.response?.data?.detail || 'Failed to create event');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <Button
          onClick={() => navigate('/events')}
          variant="ghost"
          className="mb-6 hover:bg-gray-100 rounded-full"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>

        <Card className="shadow-xl border-none">
          <CardHeader>
            <CardTitle className="text-3xl">Create New Event</CardTitle>
            <CardDescription>Fill in the details to create your event</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Event Details */}
              <div className="space-y-4">
                <div>
                  <Label htmlFor="title">Event Title *</Label>
                  <Input
                    data-testid="event-title-input"
                    id="title"
                    name="title"
                    value={formData.title}
                    onChange={handleInputChange}
                    placeholder="Enter event title"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="description">Description *</Label>
                  <Textarea
                    data-testid="event-description-input"
                    id="description"
                    name="description"
                    value={formData.description}
                    onChange={handleInputChange}
                    placeholder="Describe your event"
                    rows={4}
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="date">Date & Time *</Label>
                    <Input
                      data-testid="event-date-input"
                      id="date"
                      name="date"
                      type="datetime-local"
                      value={formData.date}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="category">Category *</Label>
                    <Select value={formData.category} onValueChange={handleCategoryChange}>
                      <SelectTrigger data-testid="event-category-select">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        {categories.map((cat) => (
                          <SelectItem key={cat.id} value={cat.name}>{cat.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="location">Location *</Label>
                    <Input
                      data-testid="event-location-input"
                      id="location"
                      name="location"
                      value={formData.location}
                      onChange={handleInputChange}
                      placeholder="Event venue or address"
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="capacity">Capacity *</Label>
                    <Input
                      data-testid="event-capacity-input"
                      id="capacity"
                      name="capacity"
                      type="number"
                      min="1"
                      value={formData.capacity}
                      onChange={handleInputChange}
                      placeholder="Maximum attendees"
                      required
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="image_url">Event Image URL (Optional)</Label>
                  <Input
                    data-testid="event-image-input"
                    id="image_url"
                    name="image_url"
                    value={formData.image_url}
                    onChange={handleInputChange}
                    placeholder="https://example.com/image.jpg"
                  />
                </div>
              </div>

              {/* Ticket Types */}
              <div className="border-t pt-6">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-xl font-bold">Ticket Types</h3>
                  <Button
                    data-testid="add-ticket-type-btn"
                    type="button"
                    onClick={addTicketType}
                    variant="outline"
                    className="rounded-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Ticket Type
                  </Button>
                </div>

                {ticketTypes.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No ticket types added yet</p>
                ) : (
                  <div className="space-y-4">
                    {ticketTypes.map((ticket, index) => (
                      <Card key={index} data-testid={`ticket-type-card-${index}`} className="p-4 bg-gray-50">
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                          <div className="md:col-span-1">
                            <Label>Ticket Name *</Label>
                            <Input
                              data-testid={`ticket-name-input-${index}`}
                              value={ticket.name}
                              onChange={(e) => updateTicketType(index, 'name', e.target.value)}
                              placeholder="e.g., General"
                              required
                            />
                          </div>
                          <div>
                            <Label>Price ($) *</Label>
                            <Input
                              data-testid={`ticket-price-input-${index}`}
                              type="number"
                              step="0.01"
                              min="0"
                              value={ticket.price}
                              onChange={(e) => updateTicketType(index, 'price', e.target.value)}
                              placeholder="0.00"
                              required
                            />
                          </div>
                          <div>
                            <Label>Quantity *</Label>
                            <Input
                              data-testid={`ticket-quantity-input-${index}`}
                              type="number"
                              min="1"
                              value={ticket.quantity_available}
                              onChange={(e) => updateTicketType(index, 'quantity_available', e.target.value)}
                              placeholder="100"
                              required
                            />
                          </div>
                          <div className="flex items-end">
                            <Button
                              data-testid={`remove-ticket-btn-${index}`}
                              type="button"
                              onClick={() => removeTicketType(index)}
                              variant="destructive"
                              className="w-full"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>

              <Button
                data-testid="create-event-submit-btn"
                type="submit"
                disabled={loading}
                className="w-full py-6 text-lg bg-blue-600 hover:bg-blue-700 text-white rounded-full"
              >
                {loading ? 'Creating Event...' : 'Create Event'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CreateEvent;
